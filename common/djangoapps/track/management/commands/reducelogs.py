"""TODO"""

from django.core.management.base import BaseCommand

from student.models import CourseEnrollment
from track.models import TrackingLog, SessionLog


class Command(BaseCommand):
    """
        Management Command reducelogs for tracking logs
    """
    def handle(self, *args, **options):
        """
            Body of reducelogs command
        """
        valid_logs = self.clean_tracking_logs(TrackingLog.objects.all().order_by('time'))
        users_with_logs = TrackingLog.objects.order_by().values('username').distinct()
        courses = CourseEnrollment.objects.order_by().values('course_id').distinct()
        reduced_logs = self.reduce_user_logs(users_with_logs, valid_logs, courses)
        self.load_session_logs(reduced_logs)
        self.stdout.write('command finished')

    def clean_tracking_logs(self, queryset):
        """
            returns a list of valid logs to be reduced
        """
        logs = [log for log in queryset if self.is_valid(log)]

        return logs

    def is_valid(self, log):
        """
            for a log to be valid must have a course_id on event_type field
        """
        is_valid = False
        course_id = None
        try:
            splitted_event = log.event_type.split("/")
            if 'course-' in splitted_event[2]:
                course_id = splitted_event[2]
        except Exception:
            self.stdout.write('course_id not found on log ')
        else:
            if course_id:
                is_valid = True

        return is_valid

    @staticmethod
    def get_user_course_logs(logs, course):
        """
            it returns the logs for a course
        """
        user_course_logs = []

        for log in logs:
            splitted_event = log.event_type.split("/")
            course_id = splitted_event[2]
            if course.get('course_id') == course_id:
                user_course_logs.append(log)

        return user_course_logs

    def split_logs_by_session(self, user_course_logs, session_duration):
        """
            method in charge of grouping tracking events
            as session events
        """

        result = []
        acc_list = [user_course_logs[0]]
        for index in range(1, len(user_course_logs)):

            if self.difference(user_course_logs[index - 1], user_course_logs[index]) <= session_duration:
                acc_list.append(user_course_logs[index])
            else:
                result.append(acc_list)
                acc_list = []
                acc_list.append(user_course_logs[index])

        if acc_list:
            result.append(acc_list)

        return filter(lambda x: len(x) >= 2, result)

    @staticmethod
    def difference(log1, log2):
        """
            computes the time difference between two tracking logs in seconds
        """
        diff = log2.time - log1.time
        return diff.total_seconds()

    def generate_session_logs(self, logslist):
        """
            it returns a session log object for every tracking log object in logs
        """
        session_logs = []

        for logs in logslist:
            session_object = {}
            try:
                splitted_event = logs[0].event_type.split("/")
                course_id = splitted_event[2]
            except Exception:
                self.stdout.write('could not get course_id')
            else:
                session_object = {
                    'username': logs[0].username,
                    'host': logs[0].host,
                    'course_id': course_id,
                    'session_start': logs[0].time,
                    'session_end': logs[-1].time,
                }

                session_logs.append(session_object)

        return session_logs

    def reduce_user_logs(self, users, valid_logs, courses, session_duration=480.0):
        """
            parameter session_duration is in secconds

            This method should return a list with session logs per user
            group by time difference between tracking logs events.
            A session log has this attributes:
            - username
            - courseid
            - session start
            - session end
            - host
        """
        session_logs = []

        for user in users:
            username = user.get('username')
            if username:
                logs_generated_by_user = filter(lambda x: x.username == username, valid_logs)
                for course in courses:
                    user_course_logs = self.get_user_course_logs(logs_generated_by_user, course)
                    if user_course_logs:
                        splitted_course_logs = self.split_logs_by_session(user_course_logs, session_duration)
                        session_logs += self.generate_session_logs(splitted_course_logs)

        return session_logs

    def load_session_logs(self, loglist):
        """
            creates session log db records
        """
        for session_log in loglist:
            SessionLog.objects.create(
                username=session_log['username'],
                host=session_log['host'],
                courseid=session_log['course_id'],
                start_time=session_log['session_start'],
                end_time=session_log['session_end']
            )
        self.stdout.write('session logs loaded on database')
