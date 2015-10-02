"""
URLs for the Management API

"""
from django.conf.urls import patterns, url
from manage_api.views import UserManagement


urlpatterns = patterns(
    'manage_api.views',
    url(
        r'^v1/users/$',
        UserManagement.as_view(),
        name="manage_users_api"
    ),
)
