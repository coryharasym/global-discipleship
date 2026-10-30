from datetime import datetime,time,timezone
from zoneinfo import ZoneInfo
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .models import Profile,Band,Membership,JoinRequest
from .services import join,review,next_meeting

class PhaseOneTests(TestCase):
    @classmethod
    def person(cls,name,gender='men'):
        u=User.objects.create_user(name,f'{name}@example.com','Strong-test-password-72')
        Profile.objects.create(user=u,display_name=name,gender=gender,timezone='Europe/London')
        return u
    @classmethod
    def setUpTestData(cls):
        cls.host=cls.person('host');cls.alex=cls.person('alex');cls.sam=cls.person('sam');cls.woman=cls.person('woman','women')
        cls.band=Band.objects.create(host=cls.host,name='A circle of grace',gender='men',day=2,time=time(19),timezone='America/Edmonton',description='Pray together',private_details='SECRET MEETING ADDRESS',capacity=5)
        Membership.objects.create(band=cls.band,user=cls.host)
    def approve(self,user):
        join(self.band.pk,user,'Hello');review(JoinRequest.objects.get(user=user).pk,self.host,True)
    def test_registration(self):
        response=self.client.post('/register/',{'username':'new','full_name':'Private Full Name','email':'new@example.com','password1':'Brand-new-password-56','password2':'Brand-new-password-56','adult':'on'})
        self.assertRedirects(response,'/profile/')
        self.assertEqual(User.objects.get(username='new').first_name,'Private Full Name')
        self.assertRedirects(self.client.get('/start/'),'/profile/')
    def test_age_password_and_duplicate_email(self):
        response=self.client.post('/register/',{'username':'new','full_name':'Name','email':'host@example.com','password1':'123','password2':'123'})
        self.assertEqual(response.status_code,200)
        self.assertFalse(User.objects.filter(username='new').exists())
    def test_eligibility_and_public_privacy(self):
        self.client.force_login(self.woman)
        self.assertNotContains(self.client.get('/'),'A circle of grace')
        self.assertEqual(self.client.get(f'/bands/{self.band.pk}/').status_code,403)
        with self.assertRaises(ValidationError): join(self.band.pk,self.woman,'Hello')
        self.client.force_login(self.alex)
        r=self.client.get('/')
        self.assertContains(r,'A circle of grace');self.assertNotContains(r,'SECRET MEETING ADDRESS');self.assertNotContains(r,'host@example.com')
        self.assertNotContains(self.client.get(f'/bands/{self.band.pk}/'),'SECRET MEETING ADDRESS')
    def test_host_approval_and_activation(self):
        self.client.force_login(self.alex)
        self.client.post(f'/bands/{self.band.pk}/',{'introduction':'Hello'})
        req=JoinRequest.objects.get(user=self.alex)
        self.assertEqual(self.client.post(f'/requests/{req.pk}/review/',{'decision':'accept'}).status_code,404)
        self.client.force_login(self.host)
        self.client.post(f'/requests/{req.pk}/review/',{'decision':'accept'})
        self.assertEqual(self.client.get(f'/bands/{self.band.pk}/workspace/').status_code,403)
        self.approve(self.sam)
        self.assertContains(self.client.get(f'/bands/{self.band.pk}/workspace/'),'SECRET MEETING ADDRESS')
        self.assertEqual(self.band.status,'Active')
        self.assertContains(self.client.get('/'),'A circle of grace')
        self.client.force_login(self.woman)
        self.assertEqual(self.client.get(f'/bands/{self.band.pk}/workspace/').status_code,403)
    def test_capacity_and_duplicate_requests(self):
        self.band.capacity=3;self.band.save()
        join(self.band.pk,self.alex,'Hello')
        with self.assertRaises(ValidationError): join(self.band.pk,self.alex,'Duplicate')
        join(self.band.pk,self.sam,'Hello');extra=self.person('extra');join(self.band.pk,extra,'Hello')
        for user in [self.alex,self.sam,extra]: review(JoinRequest.objects.get(user=user).pk,self.host,True)
        self.assertEqual(self.band.count,3)
        self.assertEqual(JoinRequest.objects.get(user=extra).status,'full')
        self.assertEqual(self.band.status,'Full')
        self.client.force_login(extra);self.assertNotContains(self.client.get('/'),'A circle of grace')
    def test_withdraw_and_decline(self):
        join(self.band.pk,self.alex,'Hello');req=JoinRequest.objects.get(user=self.alex)
        self.client.force_login(self.sam)
        self.assertEqual(self.client.post(f'/requests/{req.pk}/withdraw/').status_code,404)
        self.client.force_login(self.alex);self.client.post(f'/requests/{req.pk}/withdraw/')
        req.refresh_from_db();self.assertEqual(req.status,'withdrawn')
        with self.assertRaises(ValidationError): review(req.pk,self.host,True)
        join(self.band.pk,self.sam,'Hello');req=JoinRequest.objects.get(user=self.sam);review(req.pk,self.host,False)
        req.refresh_from_db();self.assertEqual(req.status,'declined')
    def test_csrf_and_get_mutations(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.host)
        self.assertEqual(c.post(f'/bands/{self.band.pk}/leave/').status_code,403)
        self.assertEqual(c.get(f'/bands/{self.band.pk}/leave/').status_code,405)
    def test_profile_eligibility_is_stable(self):
        self.client.force_login(self.host)
        r=self.client.post('/profile/',{'display_name':'Host','gender':'women','language':'English','timezone':'UTC','meeting_format':'online','radius':25})
        self.assertContains(r,'Leave your bands')
        self.host.profile.refresh_from_db();self.assertEqual(self.host.profile.gender,'men')
    def test_nearby_without_permission_and_global_search(self):
        self.client.force_login(self.alex)
        self.assertContains(self.client.get('/?mode=near'),'Nearby discovery needs')
        self.assertContains(self.client.get('/?mode=online'),'A circle of grace')
        self.assertNotContains(self.client.get('/?mode=city'),'A circle of grace')
    def test_non_latin_city_and_proximity(self):
        p=self.alex.profile;p.country='日本';p.city='東京';p.location_discovery=True;p.latitude=35.68;p.longitude=139.76;p.save()
        self.band.country='日本';self.band.city='東京';self.band.meeting_format='in_person';self.band.latitude=35.69;self.band.longitude=139.77;self.band.save()
        self.client.force_login(self.alex)
        for mode in ['near','city','country']: self.assertContains(self.client.get('/?mode='+mode),'A circle of grace')
        self.assertNotContains(self.client.get('/?mode=online'),'A circle of grace')
    def test_creation_and_validation(self):
        self.client.force_login(self.alex)
        data={'name':'Together in hope','gender':'men','language':'English','meeting_format':'online','day':1,'time':'19:00','timezone':'Asia/Tokyo','capacity':5,'description':'A shared journey','recruitment_open':'on','lifecycle':'current'}
        self.assertEqual(self.client.post('/start/',data).status_code,302)
        b=Band.objects.get(name='Together in hope');self.assertEqual(b.count,1)
        data['capacity']=6
        self.assertEqual(self.client.post('/start/',data).status_code,200)
    def test_only_host_can_edit(self):
        self.client.force_login(self.alex);self.assertEqual(self.client.get(f'/bands/{self.band.pk}/edit/').status_code,404)
    def test_private_access_revoked_on_leaving(self):
        self.approve(self.alex);self.approve(self.sam)
        self.client.force_login(self.alex)
        self.client.post(f'/bands/{self.band.pk}/leave/')
        self.assertEqual(self.client.get(f'/bands/{self.band.pk}/workspace/').status_code,403)
        self.client.force_login(self.host)
        self.assertEqual(self.client.get(f'/bands/{self.band.pk}/workspace/').status_code,403)
    def test_host_deletion_transfers_band(self):
        self.approve(self.alex);self.client.force_login(self.host)
        self.client.post('/account/delete/',{'password':'Strong-test-password-72'})
        self.assertFalse(User.objects.filter(pk=self.host.pk).exists())
        self.band.refresh_from_db();self.assertEqual(self.band.host_id,self.alex.pk)
    def test_closed_and_inactive_bands(self):
        self.band.recruitment_open=False;self.band.save()
        with self.assertRaises(ValidationError): join(self.band.pk,self.alex,'Hello')
        self.band.lifecycle='inactive';self.band.save();self.assertEqual(self.band.status,'Inactive')
    def test_display_uses_member_timezone(self):
        self.client.force_login(self.alex)
        expected=next_meeting(self.band).astimezone(ZoneInfo('Europe/London')).strftime('%H:%M')
        self.assertContains(self.client.get(f'/bands/{self.band.pk}/'),expected)
    def test_dst_spring_gap_and_fall_overlap(self):
        self.band.day=6;self.band.time=time(2,30);self.band.timezone='America/New_York'
        self.assertEqual(next_meeting(self.band,datetime(2026,3,7,12,tzinfo=timezone.utc)).day,15)
        self.band.time=time(1,30)
        self.assertEqual(next_meeting(self.band,datetime(2026,10,31,12,tzinfo=timezone.utc)).astimezone(timezone.utc).hour,5)
    def test_auth_rate_limit(self):
        for _ in range(20): self.client.post('/login/',{'username':'unknown','password':'wrong'})
        self.assertEqual(self.client.post('/login/',{'username':'unknown','password':'wrong'}).status_code,429)
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_account_recovery(self):
        self.assertEqual(self.client.post('/password-reset/',{'email':'alex@example.com'}).status_code,302)
        self.assertEqual(len(mail.outbox),1)
        uid=urlsafe_base64_encode(force_bytes(self.alex.pk));token=default_token_generator.make_token(self.alex)
        response=self.client.get(f'/reset/{uid}/{token}/')
        self.assertEqual(self.client.post(response.url,{'new_password1':'Reset-strong-password-71','new_password2':'Reset-strong-password-71'}).status_code,302)
        self.alex.refresh_from_db();self.assertTrue(self.alex.check_password('Reset-strong-password-71'))
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",EMAIL_HOST="localhost",EMAIL_HOST_USER="")
    def test_unconfigured_recovery_is_explicit(self):
        self.assertContains(self.client.post('/password-reset/',{'email':'alex@example.com'}),'Email recovery is not configured')
    def test_all_public_and_member_pages(self):
        for url in ['/','/register/','/login/','/help/','/password-reset/']: self.assertEqual(self.client.get(url).status_code,200)
        self.client.force_login(self.host)
        for url in ['/','/profile/','/my-bands/','/start/',f'/bands/{self.band.pk}/']: self.assertEqual(self.client.get(url).status_code,200)
