from util.organizations_helpers import add_organization


def add_organization_from_short_name(short_name):

    org_data = {
        "name": short_name,
        "short_name": short_name,
        "description": "Organization {}".format(short_name),
    }
    return add_organization(org_data)
