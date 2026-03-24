from django.urls import path
from . import views

# urlpatterns = [
#     path('', views.homepage, name='homepage'),
#     path('how-it-works/', views.how_it_works , name='how_it_works'),
# ]

urlpatterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('how-it-works/', views.HowItWorksView.as_view(), name='how_it_works'),
]

