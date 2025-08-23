"""
Tests for the tags api
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Recipe,
)

from recipe.serializers import TagsSerializer


TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """ Create and return a tag detail URL """
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='testpass123'):
    """ Create a new user """
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsApiTests(TestCase):
    """ Test unauthenticated tags API access. """
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test that authentication is required to access the tags API. """
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsApiTests(TestCase):
    """ Test authenticated tags API access. """
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ Test retrieving a list of tags. """
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagsSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tag_limited_to_user(self):
        """ Test that tags returned are for the authenticated user. """
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='Fruit')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual( len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)


    def test_update_tag(self):
        """ Test updating a tag. """
        tag = Tag.objects.create(user=self.user, name='After Dinner')
        payload = {'name': 'Dessert'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """ Test deleting a tag. """
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        url = detail_url(tag.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """ Test filtering tags by those assigned to recipes. """
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Dessert')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            price=Decimal('3.99'),
            time_minutes=5,
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        s1 = TagsSerializer(tag1)
        s2 = TagsSerializer(tag2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """ Test that the filtered tags are unique. """
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Dessert')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            price=Decimal('3.99'),
            time_minutes=5,
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Test Recipe 2',
            price=Decimal('4.99'),
            time_minutes=10,
        )
        recipe.tags.add(tag1)
        recipe2.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)