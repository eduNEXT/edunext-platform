"""
Helper methods for the LMS.
"""

from django.conf import settings


def get_parent_unit(xblock):
    """
    Finds xblock's parent unit if it exists.

    To find an xblock's parent unit, we traverse up the xblock's
    family tree until we find an xblock whose parent is a
    sequential xblock, which guarantees that the xblock is a unit.
    The `get_parent()` call on both the xblock and the parent block
    ensure that we don't accidentally return that a unit is its own
    parent unit.

    Returns:
        xblock: Returns the parent unit xblock if it exists.
        If no parent unit exists, returns None
    """
    while xblock:
        parent = xblock.get_parent()
        if parent is None:
            return None
        grandparent = parent.get_parent()
        if grandparent is None:
            return None
        if parent.category == "vertical" and grandparent.category == "sequential":
            return parent
        xblock = parent


def is_unit(xblock):
    """
    Checks whether the xblock is a unit.

    Get_parent_unit() returns None if the current xblock either does
    not have a parent unit or is itself a unit.
    To make sure that get_parent_unit() isn't returning None because
    the xblock is an orphan, we check that the xblock has a parent.

    Returns:
        True if the xblock is itself a unit, False otherwise.
    """

    return get_parent_unit(xblock) is None and xblock.get_parent()


def use_learning_legacy_frontend() -> bool:
    """
    THIS WILL BE OBSOLETE FROM VERSIONS HIGHER THAN NUTMEG
    https://docs.openedx.org/en/latest/community/release_notes/olive.html#learning-mfe-is-now-required
    
    Checks in django settings if use the learning legacy
    frontend instead the learning mfe.

    Returns:
        True if the legacy frontend setting is activated, by default
        legacy would be activated.
    """
    return bool(getattr(settings, "USE_LEARNING_LEGACY_FRONTEND", True))
