from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    (r'^$', 'registration.views.index'),
    (r'^openid/', include('django_mojeid.urls')),
)
