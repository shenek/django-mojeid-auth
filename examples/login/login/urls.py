from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    (r'^$', 'login.views.login'),
    (r'^openid/', include('django_mojeid.urls')),
)
