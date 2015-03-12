from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^changelang/$', 'edraak_i18n.views.set_language', name='edraak_setlang'),
)
