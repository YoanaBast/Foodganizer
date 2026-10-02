from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from core.views import handler405
from unittest.mock import patch

class HomepageViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_homepage(self):
        response = self.client.get(reverse('homepage'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/homepage.html')

class Handler405Test(TestCase):
    def test_returns_405_with_template(self):
        request = RequestFactory().post("/some-url/")
        response = handler405(request)

        self.assertEqual(response.status_code, 405)
        self.assertContains(response, "Method Not Allowed", status_code=405)  # adjust to your template text

    def test_uses_correct_template(self):
        request = RequestFactory().get("/")
        with self.assertTemplateUsed("405.html"):
            response = handler405(request)

        self.assertEqual(response.status_code, 405)

    def test_renders_405_template(self):
        request = RequestFactory().get("/")
        with patch("core.views.render") as mock_render:
            handler405(request)
        mock_render.assert_called_once_with(request, "405.html", status=405)


# add middleware tests later, think about the abscract model here, mixins