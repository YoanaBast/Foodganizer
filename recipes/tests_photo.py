import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from recipes.forms import RecipeForm
from recipes.models import Recipe


def make_image(size=(10, 10), name='x.png'):
    buf = io.BytesIO()
    Image.new('RGB', size, 'red').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class RecipePhotoTests(TestCase):
    DATA = {'name': 'soup', 'instructions': 'boil', 'hours': 0, 'minutes': 5, 'servings': 1}

    def test_photo_url_falls_back_to_default(self):
        self.assertIn('default_food', Recipe(name='x').photo_url)

    def test_form_accepts_valid_image(self):
        f = RecipeForm(self.DATA, {'photo': make_image()})
        f.is_valid()
        self.assertNotIn('photo', f.errors)

    def test_form_rejects_oversized_image(self):
        big = make_image()
        big.size = 6 * 1024 * 1024
        f = RecipeForm(self.DATA, {'photo': big})
        f.is_valid()
        self.assertIn('photo', f.errors)

    def test_form_rejects_non_image(self):
        bad = SimpleUploadedFile('x.png', b'not an image', content_type='image/png')
        f = RecipeForm(self.DATA, {'photo': bad})
        f.is_valid()
        self.assertIn('photo', f.errors)
