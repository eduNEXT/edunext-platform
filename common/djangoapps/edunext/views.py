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
        # Now the existence of the task by id is not validated

        result = None
        if task_res.ready():
            result = task_res.result

        response = {
            "state": task_res.state,
            "result": result,
        }

        return Response(response)
