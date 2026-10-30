import hashlib
from datetime import timedelta
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponse
from .models import AuthAttempt
class LocalTimezone:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        try:
            if request.user.is_authenticated: timezone.activate(ZoneInfo(request.user.profile.timezone))
            else: timezone.deactivate()
        except (AttributeError,ZoneInfoNotFoundError): timezone.deactivate()
        try: return self.get_response(request)
        finally: timezone.deactivate()
class AuthThrottle:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method=='POST' and (request.path in ['/login/','/register/','/password-reset/'] or request.path.startswith('/reset/')):
            now=timezone.now();key=hashlib.sha256((request.META.get('REMOTE_ADDR','')+request.path).encode()).hexdigest()
            with transaction.atomic():
                AuthAttempt.objects.filter(started__lt=now-timedelta(minutes=15)).delete()
                obj,_=AuthAttempt.objects.get_or_create(key=key,defaults={'started':now})
                if obj.count>=20:
                    response=HttpResponse('Too many attempts. Try again in 15 minutes.',status=429);response['Retry-After']='900';return response
                obj.count+=1;obj.save(update_fields=['count'])
        return self.get_response(request)
