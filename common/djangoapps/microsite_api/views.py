from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from microsite_configuration.models import Microsite
from microsite_api.serializers import MicrositeSerializer, MicrositeMinimalSerializer


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


@api_view(['GET', 'POST'])
def microsite_list(request):
    """
    List all microsites, or create a new microsite.
    """
    if request.method == 'GET':
        microsite = Microsite.objects.all()
        serializer = MicrositeMinimalSerializer(microsite, many=True)
        return JSONResponse(serializer.data)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = MicrositeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JSONResponse(serializer.data, status=201)
        return JSONResponse(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
def microsite_detail(request, key):
    """
    Retrieve, update or delete a microsite.
    """
    try:
        microsite = Microsite.objects.get(key=key)
    except Microsite.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = MicrositeSerializer(microsite)
        return JSONResponse(serializer.data)

    elif request.method == 'PUT':
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

    elif request.method == 'DELETE':
        microsite.delete()
        return HttpResponse(status=204)
