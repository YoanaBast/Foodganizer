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
    # http_method_names = ['post'] # test 405 -> works 3/24

    # def get(self, request, *args, **kwargs):
        # # test 400 -> works 3/24
        # raise SuspiciousOperation("test")
        # return super().get(request, *args, **kwargs)

        # test 403  -> works 3/24
        # raise PermissionDenied("test")
        # return super().get(request, *args, **kwargs)

        # test 500  -> works 3/24
        # raise Exception("test")
        # return super().get(request, *args, **kwargs)


class HowItWorksView(TemplateView):
    template_name = 'core/how_it_works.html'


def handler405(request, exception=None):
    """django does not have a 405 handler by default"""
    return render(request, '405.html', status=405)
