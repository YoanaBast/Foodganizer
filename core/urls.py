from django.contrib.sitemaps.views import sitemap
from django.urls import path
from . import views
from .sitemaps import StaticViewSitemap

# urlpatterns = [
#     path('', views.homepage, name='homepage'),
#     path('how-it-works/', views.how_it_works , name='how_it_works'),
# ]
sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('how-it-works/', views.HowItWorksView.as_view(), name='how_it_works'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),

]


