"""
Tasks for Survey Report.
"""


import logging

from celery import shared_task
from cache_lock import cache_lock
from .api import generate_report

log = logging.getLogger('edx.celery.task')


@shared_task(name='openedx.features.survey_report.tasks.generate_survey_report')
@cache_lock("generate_survey_report_lock", expire=60)
def generate_survey_report():
    """
    Tasks to generate a new survey report with non-sensitive data.
    """
    log.info(
        'Started - generate survey report'
    )

    try:
        generate_report()
        log.info('Done - generate survey report')
    except (Exception, ):  # pylint: disable=broad-except
        log.error('Error - generate survey report')
