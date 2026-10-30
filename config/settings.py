import os,secrets
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
STATE=BASE_DIR/'.local'
STATE.mkdir(mode=0o700,exist_ok=True)
key=STATE/'signing-key'
if not key.exists():
    try:
        with open(key,'x',opener=lambda p,f:os.open(p,f,0o600)) as handle: handle.write(secrets.token_urlsafe(64))
    except FileExistsError: pass
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY') or key.read_text()
DEBUG=os.environ.get('DJANGO_DEBUG','0')=='1'
ALLOWED_HOSTS=os.environ.get('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','bands']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.locale.LocaleMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','bands.middleware.LocalTimezone','bands.middleware.AuthThrottle','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','django.template.context_processors.i18n']}}]
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':STATE/'db.sqlite3','OPTIONS':{'timeout':30}}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
USE_TZ=True
USE_I18N=True
TIME_ZONE='UTC'
LANGUAGE_CODE='en'
LANGUAGES=[('en','English'),('es','Español'),('pt','Português'),('fr','Français'),('fa','فارسی'),('ar','العربية'),('zh-hans','简体中文')]
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/login/'
LOGIN_REDIRECT_URL='/my-bands/'
LOGOUT_REDIRECT_URL='/'
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'
SECURE_SSL_REDIRECT=os.environ.get('DJANGO_HTTPS','0')=='1'
SESSION_COOKIE_SECURE=SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE=SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS=31536000 if SECURE_SSL_REDIRECT else 0
if os.environ.get('DJANGO_TRUST_PROXY','0')=='1': SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
CSRF_TRUSTED_ORIGINS=[s for s in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if s]
EMAIL_BACKEND=os.environ.get('DJANGO_EMAIL_BACKEND','django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST=os.environ.get('EMAIL_HOST','localhost')
EMAIL_PORT=int(os.environ.get('EMAIL_PORT','587'))
EMAIL_USE_TLS=True
EMAIL_HOST_USER=os.environ.get('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.environ.get('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL=os.environ.get('DEFAULT_FROM_EMAIL','noreply@example.invalid')
EMAIL_TIMEOUT=10
