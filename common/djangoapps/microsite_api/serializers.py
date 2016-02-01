from rest_framework import serializers
from microsite_configuration.models import Microsite


class MicrositeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Microsite
        fields = ('key', 'subdomain', 'values')


class MicrositeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Microsite
        fields = ('key', 'subdomain')
