"""
Django admin page for edunext only models
"""
from django.contrib import admin

from .models import Redirection


class RedirectionAdmin(admin.ModelAdmin):
    list_display = [
        'target',
        'domain',
        'scheme',
    ]
    search_fields = ('target', 'domain',)

admin.site.register(Redirection, RedirectionAdmin)
