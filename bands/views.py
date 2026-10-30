from functools import wraps
from zoneinfo import ZoneInfo
from django.contrib import messages
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count,F
from django.http import HttpResponseForbidden,JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from .models import Profile,Band,Membership,JoinRequest,Notification
from .forms import RegistrationForm,ProfileForm,BandForm,IntroductionForm
from .services import join,review,next_meeting,distance,lock_band

def profiled(view):
    @login_required
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not Profile.objects.filter(user=request.user).exists(): return redirect('profile')
        return view(request,*args,**kwargs)
    return wrapped

def register(request):
    form=RegistrationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            user=form.save(commit=False);user.email=form.cleaned_data['email'];user.first_name=form.cleaned_data['full_name'];user.save()
        login(request,user);return redirect('profile')
    return render(request,'bands/form.html',{'form':form,'title':'Begin your journey','intro':'Create your adult account. Your email and full name stay private.'})

@login_required
def profile(request):
    obj=Profile.objects.filter(user=request.user).first()
    original_gender=obj.gender if obj else None
    form=ProfileForm(request.POST or None,instance=obj)
    if not obj and request.method=='GET': form.fields['timezone'].widget.attrs['data-detect']='true'
    if request.method=='POST' and form.is_valid():
        if original_gender and form.cleaned_data['gender']!=original_gender and (request.user.memberships.exists() or JoinRequest.objects.filter(user=request.user,status='pending').exists()):
            form.add_error('gender','Leave your bands and withdraw pending requests before changing eligibility.')
        else:
            obj=form.save(commit=False);obj.user=request.user;obj.save();messages.success(request,'Your preferences are saved.');return redirect('discover')
    return render(request,'bands/form.html',{'form':form,'title':'Your profile','profile':True,'intro':'Choose a limited display name. Location and church affiliation are optional. Your profile location and coordinates are never listed publicly.'})

def discover(request):
    if not request.user.is_authenticated: return render(request,'bands/discover.html',{'public':True})
    if not Profile.objects.filter(user=request.user).exists(): return redirect('profile')
    p=request.user.profile;mode=request.GET.get('mode','recommended')
    bands=Band.objects.annotate(n=Count('memberships')).filter(gender=p.gender,lifecycle='current',recruitment_open=True,n__lt=F('capacity')).order_by('-created')
    if mode=='online': bands=bands.filter(meeting_format='online')
    if mode in ['city','country']:
        country=request.GET.get('country') or p.country
        bands=bands.filter(country__iexact=country) if country else bands.none()
    if mode=='city':
        city=request.GET.get('city') or p.city
        bands=bands.filter(city__iexact=city) if city else bands.none()
    for field in ['country','city','area','life_stage','church','timezone','meeting_format']:
        value=request.GET.get(field,'').strip()
        if value: bands=bands.filter(**{field+'__iexact':value})
    day=request.GET.get('day','')
    if day in [str(i) for i in range(7)]: bands=bands.filter(day=int(day))
    results=[]
    my_languages={s.strip().casefold() for s in (p.language+','+p.additional_languages).split(',') if s.strip()}
    for b in bands:
        languages={s.strip().casefold() for s in (b.language+','+b.additional_languages).split(',') if s.strip()}
        language=request.GET.get('language','').strip().casefold()
        if language and language not in languages: continue
        shared=languages & my_languages
        if mode=='recommended' and not shared: continue
        reasons=[];score=0
        local=next_meeting(b).astimezone(ZoneInfo(p.timezone));b.next_local=local
        start=request.GET.get('after','');end=request.GET.get('before','')
        if start and local.strftime('%H:%M')<start: continue
        if end and local.strftime('%H:%M')>end: continue
        spaces=request.GET.get('spaces','')
        if spaces.isdigit() and b.capacity-b.count<int(spaces): continue
        if shared: score+=4;reasons.append('Shared language')
        if b.meeting_format==p.meeting_format: score+=2;reasons.append('Your preferred format')
        if p.available_day==local.weekday() and (not p.available_from or local.time()>=p.available_from) and (not p.available_until or local.time()<=p.available_until): score+=6;reasons.append('Fits your availability')
        if b.timezone==p.timezone: score+=2;reasons.append('Same time zone')
        if p.life_stage and p.life_stage.casefold()==b.life_stage.casefold(): score+=1;reasons.append('Shared life stage')
        if p.city and p.city.casefold()==b.city.casefold(): score+=3;reasons.append('In your city')
        if mode=='near':
            if not p.location_discovery or p.latitude is None or b.latitude is None or b.meeting_format=='online': continue
            km=distance(p.latitude,p.longitude,b.latitude,b.longitude)
            if km>p.radius: continue
            score+=max(0,5-km/10);reasons.append(f'About {round(km)} km away')
        b.reasons=reasons;results.append((score,b))
    if mode in ['recommended','near']: results.sort(key=lambda item:item[0],reverse=True)
    return render(request,'bands/discover.html',{'bands':[b for _,b in results],'mode':mode,'needs_location':mode=='near' and (not p.location_discovery or p.latitude is None)})

@profiled
def band_form(request,pk=None):
    band=get_object_or_404(Band,pk=pk,host=request.user) if pk else None
    form=BandForm(request.POST or None,instance=band,initial=None if band else {'gender':request.user.profile.gender,'timezone':request.user.profile.timezone,'language':request.user.profile.language})
    if request.method=='POST' and form.is_valid():
        if form.cleaned_data['gender']!=request.user.profile.gender: form.add_error('gender','Band eligibility must match your profile.')
        else:
            with transaction.atomic():
                current=lock_band(pk) if pk else None
                if current and form.cleaned_data['capacity']<current.count: form.add_error('capacity','Capacity cannot be below current membership.')
                else:
                    obj=form.save(commit=False);obj.host=request.user;obj.save()
                    Membership.objects.get_or_create(user=request.user,band=obj)
                    messages.success(request,'Your band has been saved.');return redirect('band',pk=obj.pk)
    return render(request,'bands/form.html',{'form':form,'title':'Care for your band' if pk else 'Start a band','intro':'Invite 3–5 adults into a six-month journey. List only an approximate public area. Private meeting details open at three approved members.'})

@profiled
def band_detail(request,pk):
    b=get_object_or_404(Band,pk=pk);member=b.memberships.filter(user=request.user).exists()
    if b.gender!=request.user.profile.gender or (not member and not b.available): return HttpResponseForbidden('This band is not available to your profile.')
    form=IntroductionForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try: join(pk,request.user,form.cleaned_data['introduction']);messages.success(request,'Your request was sent to the host.')
        except ValidationError as e: messages.error(request,' '.join(e.messages))
        return redirect('band',pk=pk)
    return render(request,'bands/detail.html',{'band':b,'member':member,'form':form,'existing':JoinRequest.objects.filter(band=b,user=request.user).first(),'pending':b.requests.filter(status='pending').select_related('user__profile') if b.host_id==request.user.pk else [],'next_local':next_meeting(b)})

@profiled
def my_bands(request):
    return render(request,'bands/my.html',{'memberships':request.user.memberships.select_related('band'),'requests':JoinRequest.objects.filter(user=request.user).select_related('band'),'notifications':Notification.objects.filter(user=request.user).order_by('-created')[:30]})

@profiled
@require_POST
def review_request(request,pk):
    req=get_object_or_404(JoinRequest,pk=pk,band__host=request.user)
    if request.POST.get('decision') not in ['accept','decline']: return HttpResponseForbidden()
    try: review(pk,request.user,request.POST['decision']=='accept');messages.success(request,'Request reviewed.')
    except ValidationError as e: messages.error(request,' '.join(e.messages))
    return redirect('band',pk=req.band_id)

@profiled
@require_POST
def withdraw(request,pk):
    req=get_object_or_404(JoinRequest,pk=pk,user=request.user)
    # Same band lock serializes withdrawal against host acceptance.
    with transaction.atomic():
        lock_band(req.band_id);JoinRequest.objects.filter(pk=pk,status='pending').update(status='withdrawn')
    return redirect('my_bands')

@profiled
def workspace(request,pk):
    b=get_object_or_404(Band,pk=pk)
    if not b.memberships.filter(user=request.user).exists() or b.count<3 or b.lifecycle!='current': return HttpResponseForbidden('Approved membership and at least three active members are required.')
    return render(request,'bands/workspace.html',{'band':b,'members':b.memberships.select_related('user__profile'),'next_local':next_meeting(b)})

@profiled
@require_POST
def leave(request,pk):
    with transaction.atomic():
        b=lock_band(get_object_or_404(Band,pk=pk).pk)
        b.memberships.filter(user=request.user).delete()
        if b.host_id==request.user.pk:
            successor=b.memberships.order_by('pk').first()
            if successor:
                b.host=successor.user;b.save(update_fields=['host'])
                Notification.objects.create(user=successor.user,text=f'You are now host of {b.name}.')
            else: b.delete()
    messages.success(request,'You have left the band. Private access has ended.');return redirect('my_bands')

@login_required
def delete_account(request):
    if request.method=='POST':
        if not request.user.check_password(request.POST.get('password','')): messages.error(request,'Your password did not match.')
        else:
            user=request.user
            with transaction.atomic():
                for b in user.hosted_bands.all():
                    b=lock_band(b.pk);successor=b.memberships.exclude(user=user).order_by('pk').first()
                    if successor:
                        b.host=successor.user;b.save(update_fields=['host'])
                        Notification.objects.create(user=successor.user,text=f'You are now host of {b.name}.')
                    else: b.delete()
                logout(request);user.delete()
            messages.success(request,'Your account and personal data have been deleted.');return redirect('discover')
    return render(request,'bands/delete.html')

def help_page(request): return render(request,'bands/help.html')

class RecoveryView(PasswordResetView):
    template_name='bands/form.html'
    email_template_name='bands/reset_email.txt'
    extra_context={'title':'Recover your account'}
    def form_valid(self,form):
        from django.conf import settings
        if not settings.EMAIL_HOST_USER and settings.EMAIL_HOST=='localhost' and settings.EMAIL_BACKEND=='django.core.mail.backends.smtp.EmailBackend':
            form.add_error(None,'Email recovery is not configured on this installation. Contact its operator.');return self.form_invalid(form)
        return super().form_valid(form)
