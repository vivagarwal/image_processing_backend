from django.contrib import admin
from .models import ImageProcessorRequest, ImageProcessorUpload

# Register both models
admin.site.register(ImageProcessorRequest)
admin.site.register(ImageProcessorUpload)
