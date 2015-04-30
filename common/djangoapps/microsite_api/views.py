from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from microsite_configuration.models import Microsite
from microsite_api.serializers import MicrositeSerializer, MicrositeMinimalSerializer
from microsite_api.authenticators import MicrositeManagerAuthentication


# TODO: do we need this. I just had it so from the tutorial
# See if user_api has something quite like this
class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class MicrositeList(APIView):
    """
    List all microsites, or create a new microsite.
    """

    authentication_classes = (MicrositeManagerAuthentication,)
    renderer_classes = [JSONRenderer]

    def get(self, request, format=None):
        microsite = Microsite.objects.all()
        serializer = MicrositeMinimalSerializer(microsite, many=True)
        return JSONResponse(serializer.data)

    def post(self, request, format=None):
        data = JSONParser().parse(request)
        serializer = MicrositeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)


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
            return HttpResponse(status=404)

    def get(self, request, key, format=None):
        microsite = self.get_microsite(key)
        serializer = MicrositeSerializer(microsite)
        return JSONResponse(serializer.data)

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
            return JSONResponse(serializer.data)
        return JSONResponse(serializer.errors, status=400)

    def delete(self, request, key, format=None):
        microsite = self.get_microsite(key)
        microsite.delete()
        return HttpResponse(status=204)
