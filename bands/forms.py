from zoneinfo import available_timezones
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile,Band,JoinRequest
ZONES=[(z,z) for z in sorted(available_timezones())]
class RegistrationForm(UserCreationForm):
    full_name=forms.CharField(max_length=150)
    email=forms.EmailField()
    adult=forms.BooleanField(label='I confirm I am 18 years old or older.')
    class Meta:
        model=User
        fields=['username','full_name','email','password1','password2','adult']
    def clean_email(self):
        email=self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError('An account already uses this email address.')
        return email
class LocationForm(forms.ModelForm):
    def clean(self):
        d=super().clean()
        if (d.get('latitude') is None)!=(d.get('longitude') is None): raise forms.ValidationError('Enter both approximate coordinates, or leave both empty.')
        return d
class ProfileForm(LocationForm):
    timezone=forms.ChoiceField(choices=ZONES)
    class Meta:
        model=Profile
        exclude=['user']
        widgets={'introduction':forms.Textarea(attrs={'rows':3}),'available_from':forms.TimeInput(attrs={'type':'time'}),'available_until':forms.TimeInput(attrs={'type':'time'})}
    def clean(self):
        d=super().clean()
        if d.get('available_from') and d.get('available_until') and d['available_from']>d['available_until']: raise forms.ValidationError('Use a same-day availability window with the end after the start.')
        return d
class BandForm(LocationForm):
    timezone=forms.ChoiceField(choices=ZONES)
    class Meta:
        model=Band
        exclude=['host','created']
        widgets={'time':forms.TimeInput(attrs={'type':'time'}),'description':forms.Textarea(attrs={'rows':4}),'private_details':forms.Textarea(attrs={'rows':3})}
        help_texts={'private_details':'Exact address or meeting link. Only approved members of an active band can access this.','area':'General public meeting area only. Never enter a home address.'}
    def clean(self):
        d=super().clean()
        if d.get('meeting_format')!='online' and (not d.get('country') or not d.get('city')): raise forms.ValidationError('In-person and hybrid bands need a country and city.')
        return d
class IntroductionForm(forms.ModelForm):
    class Meta:
        model=JoinRequest
        fields=['introduction']
        widgets={'introduction':forms.Textarea(attrs={'rows':4})}
