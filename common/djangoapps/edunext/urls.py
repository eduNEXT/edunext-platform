"""
URLs for the Microsite API

"""
from django.conf.urls import patterns, url, include

from routers import router
from views import CeleryTasksStatus


urlpatterns = patterns(
    '',
    url(r'^data-api/v1/', include(router.urls, namespace='ednx-data-api')),
    url(r'^data-api/v1/tasks/(?P<task_id>.*)$', CeleryTasksStatus.as_view(), name="celery-data-api-tasks"),
)
