from django.urls import path
from .views import UploadCSV

urlpatterns = [
    path('upload', UploadCSV.as_view(), name='upload_csv'),
]
