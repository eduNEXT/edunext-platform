#!/usr/bin/python
# -*- coding: utf-8 -*-
from celery.result import AsyncResult

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from microsite_api.authenticators import MicrositeManagerAuthentication


class CeleryTasksStatus(APIView):
    """
    view to check celery tasks status
    """
    authentication_classes = (MicrositeManagerAuthentication,)

    def get(self, request, task_id=None, *args, **kwargs):
        """
        Return the task status and its result, if already calculated.
        """
        if not task_id:
            raise NotFound()

        task_res = AsyncResult(task_id)
        # Provisional way to check if a task exists in celery or not
        # TODO: look for a better way to do this
        if task_res.state == "PENDING":
            raise NotFound("The task_id does not exist")

        response = {
            "state": task_res.state,
            "result": task_res.result,
        }

        return Response(response)
