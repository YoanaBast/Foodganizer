from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.core.signing import Signer, BadSignature
from django.utils.deprecation import MiddlewareMixin


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


class IPRateLimitMiddleware(MiddlewareMixin):
    cache_key_prefix = 'rate_limit_ip'
    window_seconds = 30

    def process_request(self, request):
        allowed_requests = getattr(settings, 'REQUESTS_PER_MINUTE', 20)
        now = timezone.now().timestamp()
        window_start = now - self.window_seconds

        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        if ',' in ip:  # X-Forwarded-For can contain multiple IPs, take the first
            ip = ip.split(',')[0].strip()

        session_key = f'{self.cache_key_prefix}_{ip}'
        recent_timestamps = [
            t
            for t in request.session.get(session_key, [])
            if t > window_start
        ]

        if len(recent_timestamps) >= allowed_requests:
            return render(request, '429.html', status=429)

        recent_timestamps.append(now)
        request.session[session_key] = recent_timestamps
        request.session.modified = True


class SuspiciousActivityMiddleware(MiddlewareMixin):
    blocked_params = {'is_admin', 'is_staff', 'is_superuser'}

    def process_request(self, request):
        if self._has_suspicious_params(request.GET) or self._has_suspicious_params(request.POST):
            return HttpResponseForbidden("Suspicious activity detected!")

    def _has_suspicious_params(self, querydict):
        return any(key in self.blocked_params for key in querydict)