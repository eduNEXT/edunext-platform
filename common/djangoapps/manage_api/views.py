#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from itertools import chain

import logging
import mail

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from student.views import _do_create_account
from student.forms import AccountCreationForm
from student.models import create_comments_service_user
from student.roles import OrgRerunCreatorRole, OrgCourseCreatorRole
from edxmako.shortcuts import render_to_string
from django.utils.translation import override as override_language

from microsite_api.authenticators import MicrositeManagerAuthentication
from util.json_request import JsonResponse
from openedx.conf import settings
from microsite_configuration import microsite
from microsite_configuration.models import Microsite

log = logging.getLogger("edx.student")


class UserManagement(APIView):
    """
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def post(self, request, format=None):
        """
        """
        # Gather all the request data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        contact_name = request.POST.get('contact_name')
        activate = request.POST.get('activate', False)
        org_manager = request.POST.get('org_manager', False)
        send_email = request.POST.get('send_email', False)
        language = request.POST.get('language', 'en')

        conflicts = check_account_exists(email=email, username=username)
        if conflicts:
            return JsonResponse({'conflict_on_fields': conflicts}, status=409)

        data = {
            'username': username,
            'email': email,
            'password': password,
            'name': contact_name,
        }

        # Go ahead and create the new user
        with transaction.commit_on_success():
            form = AccountCreationForm(
                data=data,
                tos_required=False,
            )
            (user, profile, registration) = _do_create_account(form)

        create_comments_service_user(user)

        if send_email:
            with override_language(language):
                context = {
                    'name': profile.name,
                    'key': registration.activation_key,
                }

                # composes activation email
                subject = render_to_string('emails/activation_email_subject.txt', context)
                subject = ''.join(subject.splitlines())
                message = render_to_string('emails/activation_email.txt', context)
                message_html = None
                if (settings.FEATURES.get('ENABLE_MULTIPART_EMAIL')):
                    message_html = render_to_string('emails/html/activation_email.html', context)
                from_address = microsite.get_value(
                    'email_from_address',
                    settings.DEFAULT_FROM_EMAIL
                )
                try:
                    mail.send_mail(subject, message, from_address, [user.email], html_message=message_html)
                except Exception:  # pylint: disable=broad-except
                    log.error(u'Unable to send activation email to remotely created user from "%s"', from_address, exc_info=True)

        # Assing the user to the org management roles
        if org_manager:
            # We have to make them active for the roles to stick
            user.is_active = True
            user.save()

            creator_role = OrgCourseCreatorRole(org_manager)
            creator_role.add_users(user)
            rerun_role = OrgRerunCreatorRole(org_manager)
            rerun_role.add_users(user)

            user.is_active = False
            user.save()

        if activate:
            registration.activate()

        return JsonResponse({"success": True}, status=201)


class OrgManagement(APIView):
    """
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def post(self, request, format=None):
        """
        """
        # Gather all the request data
        organization_name = request.POST.get('organization_name')

        # Forbid org already defined in a microsite
        orgs_in_microsites = microsite.get_all_orgs()
        if organization_name.lower() in (org.lower() for org in orgs_in_microsites):
            return JsonResponse("Org taken", status=409)

        # TODO:
        # Find orgs that already have courses in them and forbid those too

        return JsonResponse({"success": True}, status=200)


class SubdomainManagement(APIView):
    """
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def post(self, request, format=None):
        """
        """
        # Gather all the request data
        subdomain = request.POST.get('subdomain')
        objects = Microsite.objects.filter(subdomain__startswith=subdomain).values_list('subdomain')

        return JsonResponse({'subdomains': list(chain.from_iterable(objects))}, status=200)
