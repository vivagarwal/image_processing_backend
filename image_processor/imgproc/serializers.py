from rest_framework import serializers
from .models import ImageProcessorRequest , ImageProcessorUpload

class ImageProcessorRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageProcessorRequest
        fields = '__all__'

class ImageProcessorUploadSerializer(serializers.ModelSerializer):
    images = ImageProcessorUpload(many=True, read_only=True)

    class Meta:
        model = ImageProcessorUpload
        fields = '__all__'
