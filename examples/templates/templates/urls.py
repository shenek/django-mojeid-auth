from django.conf.urls import patterns, include

urlpatterns = patterns(
    '',
    (r'^$', 'templates.views.index'),
    (r'^openid/', include('django_mojeid.urls')),
)
