from django.urls import path
from .views import UploadCSV,hello,check_db_connection,get_request_status

urlpatterns = [
    path('upload', UploadCSV.as_view(), name='upload_csv'),
    path('hello',hello,name="hello world"),
    path('check_db_connection',check_db_connection,name="check db connection"),
    path('status/<uuid:request_id>/', get_request_status, name='processing_status'),
]