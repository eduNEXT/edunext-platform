# lint-amnesty, pylint: disable=missing-module-docstring
import logging
from datetime import datetime
from typing import Dict

from opaque_keys.edx.keys import CourseKey
from openedx.core import types
from openedx.core.djangoapps.course_groups.partition_generator import create_team_set_partition_with_course_id

from xmodule.partitions.enrollment_track_partition_generator import (  # lint-amnesty, pylint: disable=wrong-import-order
    create_enrollment_track_partition_with_course_id
)
from xmodule.partitions.partitions import (  # lint-amnesty, pylint: disable=wrong-import-order
    ENROLLMENT_TRACK_PARTITION_ID,
)
from xmodule.partitions.partitions_service import get_user_partition_groups  # lint-amnesty, pylint: disable=wrong-import-order
from xmodule.partitions.partitions import Group  # lint-amnesty, pylint: disable=wrong-import-order

from .base import OutlineProcessor

log = logging.getLogger(__name__)


class TeamPartitionGroupsOutlineProcessor(OutlineProcessor):
    """
    Processor for applying all team user partition groups.

    Confining the processor to only EnrollmentTrack user partition is a
    significant limitation. Nonetheless, it is a step towards the goal of
    supporting all partition schemes in the future.
    """
    def __init__(self, course_key: CourseKey, user: types.User, at_time: datetime):
        super().__init__(course_key, user, at_time)
        self.team_groups: Dict[str, Group] = {}
        self.user_group = None

    def load_data(self, full_course_outline) -> None:
        """
        Pull team groups for this course and which group the user is in.
        """
        user_partitions = create_team_set_partition_with_course_id(self.course_key)
        self.team_groups = get_user_partition_groups(
            self.course_key,
            user_partitions,
            self.user,
            partition_dict_key='id'
        )
        # TODO: fix type annotation: https://github.com/openedx/tcril-engineering/issues/313
        # self.user_group = self.team_groups.get(ENROLLMENT_TRACK_PARTITION_ID)  # type: ignore
        self.user_groups = []
        for _, group in self.team_groups.items():
            self.user_groups.append(group.id)

    def _is_user_excluded_by_partition_group(self, user_partition_groups):
        """
        Is the user part of the group to which the block is restricting content?
        """
        if not user_partition_groups:
            return False

        if not self.user_groups:
            return False

        partition_intersection = set(user_partition_groups.values()) & set(self.user_groups)
        if not partition_intersection:
            return False

        return True

    def usage_keys_to_remove(self, full_course_outline):
        """
        Content group exclusions remove the content entirely.

        If you're in the Audit track, there are things in the Verified track
        that you don't even know exists. This processor always removes things
        entirely instead of making them visible-but-inaccessible (like
        ScheduleOutlineProcessor does).
        """
        removed_usage_keys = set()
        for section in full_course_outline.sections:
            remove_all_children = False
            if self._is_user_excluded_by_partition_group(
                section.user_partition_groups
            ):
                removed_usage_keys.add(section.usage_key)
                remove_all_children = True
            for seq in section.sequences:
                if remove_all_children or self._is_user_excluded_by_partition_group(
                    seq.user_partition_groups
                ):
                    removed_usage_keys.add(seq.usage_key)
        return removed_usage_keys
