from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView

# Create your views here.

from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import RegisterForm, ProfileEditForm
from .models import Profile


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

class EditProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileEditForm
    template_name = 'users/edit_profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user.profile


class CsrfFailureView(View):
    """when I go back and forward i  forms I sometimes get 503, this is to not show it to the user"""
    def dispatch(self, request, *args, **kwargs):
        messages.warning(request, "Your session expired. Please log in again.")
        return redirect('login')
csrf_failure = CsrfFailureView.as_view()