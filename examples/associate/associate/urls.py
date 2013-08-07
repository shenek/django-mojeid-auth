from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    (r'^$', 'associate.views.associate'),
    (r'^associate$', 'associate.views.display_associate'),
    (r'^disassociate$', 'associate.views.display_disassociate'),
    (r'^openid/', include('django_mojeid.urls')),
)
