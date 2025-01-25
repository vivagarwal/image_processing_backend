from django.urls import path
from .views import UploadCSV,hello

urlpatterns = [
    path('upload', UploadCSV.as_view(), name='upload_csv'),
    path('',hello,name="hello world")
]