import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPE_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])
    # where second recipe in address string come from


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Pepper'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Ghorme sabzi',
        'time_minutes': 45,
        'price': 10.00,
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email='asb@shotor.com',
            password='testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user, title='Gheyme')

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = get_user_model().objects.create_user(
            'asb2@shotor.com',
            'testpass123'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user, title='Gheyme')

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(serializer.data, res.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Cheesecake',
            'time_minutes': 60.00,
            'price': 5.00
        }

        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        serializer = RecipeSerializer(recipe)

        for key in payload.keys():
            self.assertEqual(res.data[key], serializer.data[key])
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tag"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Pumpkin pie',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60.00,
            'price': 5.00
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()

        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredient(self):
        """Test creating recipe with ingredient"""
        ingredient1 = sample_ingredient(user=self.user, name="Parsley")
        ingredient2 = sample_ingredient(user=self.user, name='Mint')
        payload = {
            'title': 'Weed cake',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 60,
            'price': 15.00
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()

        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating recipe with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Almond')

        payload = {'title': 'Morassa polo', 'tags': [new_tag.id]}
        self.client.patch(detail_url(recipe.id), payload)

        recipe.refresh_from_db()

        self.assertEqual(payload['title'], recipe.title)
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))
        new_ingredient = sample_ingredient(user=self.user, name='Weed')

        payload = {
            'title': 'Weed cake',
            'ingredients': [new_ingredient.id],
            'time_minutes': 60,
            'price': 15.00
        }
        self.client.put(detail_url(recipe.id), payload)

        recipe.refresh_from_db()

        self.assertEqual(payload['title'], recipe.title)
        self.assertEqual(payload['time_minutes'], recipe.time_minutes)
        self.assertEqual(payload['price'], recipe.price)
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 1)
        self.assertIn(new_ingredient, ingredients)
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)
        self.assertEqual(recipe.user, self.user)


class RecipeImageUploadTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'sag@shotor.com',
            'testpass123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self) -> None:
        self.recipe.image.delete()  # what does this delete ?

    def test_upload_image_to_recipe(self):
        """Test uploading image to recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notImage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        """Test returning recipe with specific tags"""
        recipe1 = sample_recipe(user=self.user, title='Sabzi polo ba mahi')
        recipe2 = sample_recipe(user=self.user, title='Makaroni with meat sauce')
        tag1 = sample_tag(user=self.user, name='Seafood')
        tag2 = sample_tag(user=self.user, name='Italian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        recipe3 = sample_recipe(user=self.user, title='Masghati')
        tag3 = sample_tag(user=self.user, name='Dessert')
        recipe3.tags.add(tag3)

        res = self.client.get(
            RECIPE_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredient(self):
        """Test returning recipe with specific ingredient"""
        recipe1 = sample_recipe(user=self.user, title='Sabzi polo ba mahi')
        recipe2 = sample_recipe(user=self.user, title='Makaroni with meat sauce')
        ingredient1 = sample_ingredient(user=self.user, name='Salmon')
        ingredient2 = sample_ingredient(user=self.user, name='Spaghetti')
        recipe1.ingredient.add(ingredient1)
        recipe2.ingredient.add(ingredient2)

        recipe3 = sample_recipe(user=self.user, title='Masghati')
        ingredient3 = sample_ingredient(user=self.user, name='Flour')
        recipe3.ingredient.add(ingredient3)

        res = self.client.get(
            RECIPE_URL,
            {'tags': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
