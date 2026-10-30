from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator,MaxValueValidator
GENDERS=[('men','Men'),('women','Women')]
FORMATS=[('online','Online'),('in_person','In person'),('hybrid','Hybrid')]
DAYS=list(enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']))
class Profile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    display_name=models.CharField(max_length=60)
    gender=models.CharField(max_length=8,choices=GENDERS)
    country=models.CharField(max_length=80,blank=True)
    region=models.CharField(max_length=100,blank=True)
    city=models.CharField(max_length=100,blank=True)
    neighborhood=models.CharField(max_length=100,blank=True)
    language=models.CharField(max_length=50,default='English')
    additional_languages=models.CharField(max_length=200,blank=True)
    timezone=models.CharField(max_length=64,default='UTC')
    life_stage=models.CharField(max_length=80,blank=True)
    meeting_format=models.CharField(max_length=10,choices=FORMATS,default='online')
    available_day=models.IntegerField(choices=DAYS,null=True,blank=True)
    available_from=models.TimeField(null=True,blank=True)
    available_until=models.TimeField(null=True,blank=True)
    introduction=models.TextField(max_length=1000,blank=True)
    church=models.CharField(max_length=120,blank=True)
    hide_location=models.BooleanField(default=True)
    location_discovery=models.BooleanField(default=False)
    radius=models.PositiveIntegerField(default=25,validators=[MinValueValidator(1),MaxValueValidator(1000)])
    latitude=models.FloatField(null=True,blank=True,validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.FloatField(null=True,blank=True,validators=[MinValueValidator(-180),MaxValueValidator(180)])
class Band(models.Model):
    host=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='hosted_bands')
    name=models.CharField(max_length=100)
    gender=models.CharField(max_length=8,choices=GENDERS)
    language=models.CharField(max_length=50,default='English')
    additional_languages=models.CharField(max_length=200,blank=True)
    meeting_format=models.CharField(max_length=10,choices=FORMATS,default='online')
    country=models.CharField(max_length=80,blank=True)
    city=models.CharField(max_length=100,blank=True)
    area=models.CharField(max_length=100,blank=True)
    latitude=models.FloatField(null=True,blank=True,validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.FloatField(null=True,blank=True,validators=[MinValueValidator(-180),MaxValueValidator(180)])
    day=models.IntegerField(choices=DAYS)
    time=models.TimeField()
    timezone=models.CharField(max_length=64,default='UTC')
    capacity=models.PositiveSmallIntegerField(default=5,validators=[MinValueValidator(3),MaxValueValidator(5)])
    life_stage=models.CharField(max_length=80,blank=True)
    church=models.CharField(max_length=120,blank=True)
    description=models.TextField(max_length=2000)
    private_details=models.TextField(max_length=2000,blank=True)
    recruitment_open=models.BooleanField(default=True)
    lifecycle=models.CharField(max_length=10,choices=[('current','Current'),('inactive','Inactive'),('completed','Completed')],default='current')
    created=models.DateTimeField(auto_now_add=True)
    @property
    def count(self): return self.memberships.count()
    @property
    def status(self):
        if self.lifecycle!='current': return self.get_lifecycle_display()
        if not self.recruitment_open or self.count>=self.capacity: return 'Full'
        return 'Active' if self.count>=3 else 'Forming'
    @property
    def available(self): return self.lifecycle=='current' and self.recruitment_open and self.count<self.capacity
class Membership(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='memberships')
    band=models.ForeignKey(Band,on_delete=models.CASCADE,related_name='memberships')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','band'],name='unique_member')]
class JoinRequest(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    band=models.ForeignKey(Band,on_delete=models.CASCADE,related_name='requests')
    introduction=models.TextField(max_length=1000)
    status=models.CharField(max_length=12,default='pending',choices=[('pending','Pending'),('accepted','Accepted'),('declined','Declined'),('withdrawn','Withdrawn'),('full','Group Full')])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','band'],name='unique_request')]
class Notification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    text=models.CharField(max_length=250)
    created=models.DateTimeField(auto_now_add=True)
class AuthAttempt(models.Model):
    key=models.CharField(max_length=64,unique=True)
    count=models.PositiveIntegerField(default=0)
    started=models.DateTimeField()
