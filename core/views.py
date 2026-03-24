from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.shortcuts import render
from django.views.generic import TemplateView


# Create your views here.!

# def homepage(request):
#     return render(request, 'core/homepage.html')

# def how_it_works(request):
#     return render(request, 'core/how_it_works.html')

class HomepageView(TemplateView):
    template_name = 'core/homepage.html'



class HowItWorksView(TemplateView):
    template_name = 'core/how_it_works.html'

    # http_method_names = ['post'] # test 405 -> works 3/24 yes design - no fork

    # def get(self, request, *args, **kwargs):
        # test 400 -> works 3/24 yes design - full cat
        # raise SuspiciousOperation("test")
        # return super().get(request, *args, **kwargs)

        # test 403  -> works 3/24 yes design - locked fridge
        # raise PermissionDenied("test")
        # return super().get(request, *args, **kwargs)

        # test 500  -> works 3/24 yes design - kitchen on fire
        # raise Exception("test")
        # return super().get(request, *args, **kwargs)


def handler405(request, exception=None):
    """django does not have a 405 handler by default"""
    return render(request, '405.html', status=405)
