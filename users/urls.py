from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import LoginForm

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(form_class=LoginForm, template_name='users/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('edit-profile/', views.EditProfileView.as_view(), name='edit_profile'),

]