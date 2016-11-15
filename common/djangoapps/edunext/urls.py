"""
URLs for the Microsite API

"""
from django.conf.urls import patterns, url, include

from edunext.routers import ROUTER
from edunext.views import CeleryTasksStatus


urlpatterns = patterns(
    '',
    url(r'^data-api/v1/', include(ROUTER.urls, namespace='ednx-data-api')),
    url(r'^data-api/v1/tasks/(?P<task_id>.*)$', CeleryTasksStatus.as_view(), name="celery-data-api-tasks"),
)
