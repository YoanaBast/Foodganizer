from django.shortcuts import render
from django.core.signing import Signer, BadSignature


class Custom405Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 405:
            return render(request, '405.html', status=405)
        return response


class SignedCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.validator = Signer()

    def __call__(self, request):
        raw_cookie = request.COOKIES.get('role', '')
        try:
            request.role = self.validator.unsign(raw_cookie)
            request.role_valid = True
        except BadSignature:
            request.role = None
            request.role_valid = False

        return self.get_response(request)