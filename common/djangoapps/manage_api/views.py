#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

from django.http import HttpResponse
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from student.views import create_account_with_params, _do_create_account
from student.forms import AccountCreationForm
from student.models import create_comments_service_user
from student.roles import OrgRerunCreatorRole, OrgCourseCreatorRole

from microsite_api.authenticators import MicrositeManagerAuthentication
from microsite_api.views import JSONResponse


class UserManagement(APIView):
    """
    Retrieve, update or delete a microsite.
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

        conflicts = check_account_exists(email=email, username=username)
        if conflicts:
            return JSONResponse({'conflict_on_fields': conflicts}, status=409)

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
            if activate:
                user.is_active = True
                user.save()

        create_comments_service_user(user)

        # Assing the user to the org management roles
        if org_manager:
            creator_role = OrgCourseCreatorRole(org_manager)
            creator_role.add_users(user)
            rerun_role = OrgRerunCreatorRole(org_manager)
            rerun_role.add_users(user)

        return JSONResponse({"success": True}, status=201)
