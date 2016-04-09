"""
URLs for the Microsite API

"""
from django.conf.urls import patterns, url, include
from routers import router


urlpatterns = patterns(
    '',
    url(r'^data-api/v1/', include(router.urls, namespace='ednx-data-api')),
)
