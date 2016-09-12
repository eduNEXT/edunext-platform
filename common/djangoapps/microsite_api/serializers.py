"""
Serializer to create a representation of the microsite object

"""
import json
from rest_framework import serializers
from microsite_configuration.models import Microsite


class JSONText(serializers.Field):
    """
    """
    def to_representation(self, obj):
        return json.dumps(obj)

    def to_internal_value(self, data):
        try:
            return json.loads(data)
        except ValueError:
            raise serializers.ValidationError


class MicrositeSerializer(serializers.ModelSerializer):
    values = JSONText()

    class Meta:
        model = Microsite
        fields = ('key', 'subdomain', 'values')


class MicrositeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Microsite
        fields = ('key', 'subdomain')
