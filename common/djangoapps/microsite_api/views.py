from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from microsite_configuration.models import Microsite
from microsite_api.serializers import MicrositeSerializer, MicrositeMinimalSerializer
from microsite_api.authenticators import MicrositeManagerAuthentication
from util.json_request import JsonResponse


class MicrositeList(APIView):
    """
    List all microsites, or create a new microsite.
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def get(self, request, format=None):
        microsite = Microsite.objects.all()
        serializer = MicrositeMinimalSerializer(microsite, many=True)
        return JsonResponse(serializer.data)

    def post(self, request, format=None):
        data = JSONParser().parse(request)
        serializer = MicrositeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


class MicrositeDetail(APIView):
    """
    Retrieve, update or delete a microsite.
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def get_microsite(self, key):
        try:
            return Microsite.objects.get(key=key)
        except Microsite.DoesNotExist:
            raise Http404

    def get(self, request, key, format=None):
        microsite = self.get_microsite(key)
        serializer = MicrositeSerializer(microsite)
        return JsonResponse(serializer.data)

    def put(self, request, key, format=None):
        microsite = self.get_microsite(key)
        data = JSONParser().parse(request)

        # Don't want this altering the keys for now.
        # TODO  move this to the serializer is_valid
        # if microsite.key != data.get('key'):
        #     return JSONResponse({'error': 'Operation not allowed'}, status=400)

        serializer = MicrositeSerializer(microsite, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    def delete(self, request, key, format=None):
        microsite = self.get_microsite(key)
        microsite.delete()
        return HttpResponse(status=204)
