from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['homepage', 'meal_suggestions', 'generate_grocery_list', 'manage_fridge', 'manage_recipes', 'manage_ingredients']

    def location(self, item):
        return reverse(item)
