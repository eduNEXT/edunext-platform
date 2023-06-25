"""
Tasks for Survey Report.
"""


import logging

from celery import shared_task
from django.core.cache import cache
from .api import generate_report

log = logging.getLogger('edx.celery.task')


@shared_task(name='openedx.features.survey_report.tasks.generate_survey_report')
def generate_survey_report():
    """
    Tasks to generate a new survey report with non-sensitive data.
    """
    lock_key = 'generate_survey_report_lock'
    acquired_lock = cache.add(lock_key, 'locked', 60)

    if acquired_lock:
        log.info(
            'Started - generate survey report'
        )
        try:
            generate_report()
            log.info('Done - generate survey report')
        except (Exception, ):  # pylint: disable=broad-except
            log.error('Error - generate survey report')
        cache.delete(lock_key)
    else:
        log.warning('Warning - other worker is running this job')
