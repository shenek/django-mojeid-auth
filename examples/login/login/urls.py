from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    (r'^$', 'login.views.login'),
    (r'^new_user$', 'login.views.new_user'),
    (r'^display_user$', 'login.views.display_user'),
    (r'^openid/', include('django_mojeid.urls')),
)
