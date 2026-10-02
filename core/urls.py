from django.contrib.sitemaps.views import sitemap
from django.urls import path
from . import views
from .sitemaps import StaticViewSitemap


sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),

]


