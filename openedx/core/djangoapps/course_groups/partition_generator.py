"""
The team dynamic partition generation to be part of the
openedx.dynamic_partition plugin.
"""
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from xmodule.partitions.partitions import (
    get_partition_from_id,
    ENROLLMENT_TRACK_PARTITION_ID,
    UserPartition,
    UserPartitionError
)
from xmodule.services import TeamsConfigurationService

log = logging.getLogger(__name__)

FEATURES = getattr(settings, 'FEATURES', {})


def create_team_set_partition_with_course_id(course_id, team_sets):
    """
    Create and return the dynamic enrollment track user partition based only on course_id.
    If it cannot be created, None is returned.
    """

    try:
        team_scheme = UserPartition.get_scheme("team")
    except UserPartitionError:
        log.warning("No 'team' scheme registered, TeamUserPartition will not be created.")
        return None

    # Get team-sets from course and create user partitions for each team-set
    # Get teams from each team-set and create user groups for each team
    partitions = []
    for team_set in team_sets:
        partition = team_scheme.create_user_partition(
            id=hash(team_set.teamset_id),
            name=f"Team set {team_set.teamset_id} groups",
            description=_("Partition for segmenting users by team-set"),
            parameters={
                "course_id": str(course_id),
                "team_set_id": team_set.teamset_id,
            }
        )
        partitions.append(partition)

    return partitions


def create_team_set_partition(course):
    """
    Create and return the dynamic enrollment track user partition.
    If it cannot be created, None is returned.
    """
    used_ids = {p.id for p in course.user_partitions}
    team_sets = TeamsConfigurationService().get_teams_configuration(course.id).teamsets
    if not team_sets:
        return None

    new_team_sets = []
    for team_set in team_sets:
        if hash(team_set.teamset_id) in used_ids:
            log.warning(f"Can't add team set partition for ID {team_set['id']} in course {course}.")
            continue
        new_team_sets.append(team_set)

    return create_team_set_partition_with_course_id(course.id, new_team_sets)
