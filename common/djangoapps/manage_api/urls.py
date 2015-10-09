"""
URLs for the Management API

"""
from django.conf.urls import patterns, url
from manage_api.views import (
    UserManagement,
    OrgManagement,
    SubdomainManagement,
)


urlpatterns = patterns(
    'manage_api.views',
    url(
        r'^v1/users/$',
        UserManagement.as_view(),
        name="manage_users_api"
    ),
    url(
        r'^v1/organizations/$',
        OrgManagement.as_view(),
        name="manage_orgs_api"
    ),
    url(
        r'^v1/subdomains/$',
        SubdomainManagement.as_view(),
        name="manage_subs_api"
    ),
)
