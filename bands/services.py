from datetime import datetime,timedelta,timezone
from math import radians,sin,cos,asin,sqrt
from zoneinfo import ZoneInfo
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from .models import Band,Membership,JoinRequest,Notification

def next_meeting(band,now=None):
    now=now or datetime.now(timezone.utc)
    zone=ZoneInfo(band.timezone);local=now.astimezone(zone)
    day=local.date()+timedelta(days=(band.day-local.weekday())%7)
    for _ in range(3):
        dt=datetime.combine(day,band.time,zone)
        valid=dt.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)==dt.replace(tzinfo=None)
        if valid and dt.astimezone(timezone.utc)>now.astimezone(timezone.utc): return dt
        day+=timedelta(days=7)
    raise ValueError('Invalid recurrence')

def distance(a,b,c,d):
    a,b,c,d=map(radians,[a,b,c,d])
    return 12742*asin(min(1,sqrt(sin((c-a)/2)**2+cos(a)*cos(c)*sin((d-b)/2)**2)))

def lock_band(pk):
    # A no-op write obtains SQLite's write lock before any capacity reads.
    # PostgreSQL deployments should replace this with select_for_update.
    Band.objects.filter(pk=pk).update(recruitment_open=F('recruitment_open'))
    return Band.objects.get(pk=pk)

@transaction.atomic
def join(pk,user,text):
    band=lock_band(pk)
    if user.profile.gender!=band.gender: raise ValidationError('This band is not eligible for your profile.')
    if not band.available: raise ValidationError('This band is no longer recruiting.')
    if Membership.objects.filter(user=user,band=band).exists(): raise ValidationError('You are already a member.')
    if JoinRequest.objects.filter(user=user,band=band).exists(): raise ValidationError('A request already exists. Check My Bands.')
    JoinRequest.objects.create(user=user,band=band,introduction=text)
    Notification.objects.create(user=band.host,text=f'A join request is waiting for {band.name}.')

@transaction.atomic
def review(pk,user,accept):
    req=JoinRequest.objects.get(pk=pk);band=lock_band(req.band_id);req.refresh_from_db()
    if band.host_id!=user.pk: raise ValidationError('Only the host can review requests.')
    if req.status!='pending': raise ValidationError('This request has already been reviewed.')
    if accept:
        if req.user.profile.gender!=band.gender: raise ValidationError('This participant is no longer eligible.')
        if band.available:
            Membership.objects.create(band=band,user=req.user);req.status='accepted'
        else: req.status='full'
    else: req.status='declined'
    req.save(update_fields=['status'])
    Notification.objects.create(user=req.user,text=f'Your request for {band.name}: {req.get_status_display()}.')
