"""TODO"""

import ast

from django.core.management.base import BaseCommand

from track.models import TrackingLog


class Command(BaseCommand):
    """
        TODO
    """
    def handle(self, *args, **options):
        valid_logs = self.clean_tracking_logs(TrackingLog.objects.all().order_by('time'))
        users_with_logs = TrackingLog.objects.order_by().values('username').distinct()
        session_logs = self.reduce_user_logs(users_with_logs, valid_logs)
        # import ipdb
        # ipdb.set_trace()
        self.print_result(session_logs)
        self.stdout.write('command finished')

    def clean_tracking_logs(self, queryset):
        """
            returns a list of valid logs to be reduced
        """
        logs = [log for log in queryset if self.is_valid(log)]

        return logs

    def is_valid(self, log):
        """
            for a log to be valid must have a course_id key on context field
        """
        is_valid = False
        if log.context:
            try:
                context_dict = ast.literal_eval(log.context)
                course_id = context_dict['course_id']
            except Exception:
                self.stdout.write('error parsin or reading dict from json')
            else:
                if course_id:
                    is_valid = True

        return is_valid

    def reduce_user_logs(self, users, valid_logs, minutesdiff=8):
        """
            This method should return a list with session logs per user
            group by time difference between tracking logs events.
            A session log has this attributes:
            - username
            - courseid
            - session duration
        """
        for user in users:
            username = user.get('username')
            if username:
                logs_generated_by_user = filter(lambda x: x.username == username, valid_logs)
                # import ipdb
                # ipdb.set_trace()

            # wip fixing reduce per user problems

        return valid_logs

    def print_result(self, loglist):
        self.stdout.write('method to print result on console')
