import uuid
import os
from django.http import HttpResponse

import pandas as pd
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ImageProcessorRequest,ImageProcessorUpload
from .utils import validate_csv
# from .tasks import process_images

from django.db import connection
from django.http import JsonResponse

UPLOAD_DIR = os.path.join(os.getenv('TMP_OUTPUT_PATH'),'uploads')

class UploadCSV(APIView):
    def post(self,request,*args,**kwargs):
        file = request.FILES.get('file')

        if not file or not file.name.endswith('.csv'):
            return Response({"error": "Invalid file format. Please upload a CSV."}, status=status.HTTP_400_BAD_REQUEST)

        unique_filename = f"{uuid.uuid4()}_{file.name}"
        fs = FileSystemStorage(location=UPLOAD_DIR)
        fs.save(unique_filename, file)

        # Validate CSV
        is_valid, message = validate_csv(os.path.join(UPLOAD_DIR, unique_filename))
        if not is_valid:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new processing request
        request_id = uuid.uuid4()
        processing_request = ImageProcessorRequest.objects.create(request_id=request_id, file_name=unique_filename, status="processing")

        # # Read CSV and save data to database
        # df = pd.read_csv(os.path.join(UPLOAD_DIR, unique_filename))
        # for index, row in df.iterrows():
        #     product_image = ImageProcessorUpload.objects.create(
        #         image_processor_request=processing_request,
        #         serial_number=row['S.No.'],
        #         product_name=row['Product Name'],
        #         input_image_urls=row['Input Image Urls'],
        #     )
        #     print(row['Input Image Urls'])
        #     process_images.delay(product_image.id)
        # # image_url = "https://example.com/image.jpg"
        # # task = process_images.delay(image_url)  # Asynchronous execution

        return Response({"request_id": request_id, "message": "File uploaded successfully"}, status=status.HTTP_201_CREATED)

def hello(request):
    if request.method == "GET":
        return HttpResponse("Hello World")
    return HttpResponse("Method not allowed", status=405)

def check_db_connection(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
    return JsonResponse({'db_status': 'connected' if row else 'error'})
