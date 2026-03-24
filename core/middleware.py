from django.shortcuts import render

class Custom405Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 405:
            return render(request, '405.html', status=405)
        return response