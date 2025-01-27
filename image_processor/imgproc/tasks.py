import os
import requests
from io import BytesIO
from PIL import Image
from celery import shared_task
from .models import ImageProcessorUpload,ImageProcessorRequest
import logging
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
from django.utils import timezone
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Use absolute path to ensure images are stored correctly
OUTPUT_DIR = os.path.join(os.getenv('TMP_OUTPUT_PATH'), 'processed_images')

# Function to upload file to S3
def upload_to_s3(file_path, s3_filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')

    try:
        s3.upload_file(file_path, bucket_name, s3_filename)  # Removed ACL
        s3_url = f"https://{bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_filename}"
        return s3_url
    except NoCredentialsError:
        logger.error("AWS credentials not found.")
        return None
    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        return None

def send_webhook_notification(webhook_url, data):
    try:
        response = requests.post(webhook_url, json=data, timeout=10)
        response.raise_for_status()
        logger.info(f"Webhook sent successfully: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Failed to send webhook: {e}")

@shared_task(bind=True)
def process_images(self, request_id):
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Expected output directory: {os.path.abspath(OUTPUT_DIR)}")

    failed_flag = False
    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logger.info(f"Successfully created directory: {OUTPUT_DIR}")
        except Exception as e:
            logger.error(f"Failed to create directory {OUTPUT_DIR}: {e}")
    else:
        logger.info(f"Directory already exists: {OUTPUT_DIR}")

    # Fetch the product image record
    logger.info(f"Processing image with request ID: {request_id}")
    try:
        image_request = ImageProcessorRequest.objects.get(request_id=request_id)
        product_images = ImageProcessorUpload.objects.filter(image_processor_request=image_request)
        image_request.status = 'processing'
        image_request.save()
    except ImageProcessorRequest.DoesNotExist:
        logger.error(f"Request with ID {request_id} does not exist.")
        return

    for product_image in product_images:

        input_urls = product_image.input_image_urls.split(',')
        output_urls = []

        for url in input_urls:
            try:
                clean_url = url.strip()
                logger.info(f"Downloading image: {clean_url}")

                response = requests.get(clean_url, stream=True)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    val1 = uuid.uuid4()

                    output_filename = f"{product_image.product_name}_{val1}.jpg"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)

                    # Compress and save the image
                    img.save(output_path, "JPEG", quality=50)
                    logger.info(f"Saved compressed image at: {output_path}")

                    # Upload to S3
                    s3_url = upload_to_s3(output_path, output_filename)
                    if s3_url:
                        logger.info(f"Uploaded to S3: {s3_url}")
                        output_urls.append(s3_url)

                        # Delete the local compressed file after successful upload
                        os.remove(output_path)
                        logger.info(f"Deleted local compressed image: {output_path}")
                    else:
                        logger.error(f"Failed to upload image to S3: {output_filename}")
                        failed_flag = True
                else:
                    logger.error(f"Failed to download image {clean_url}, HTTP status code: {response.status_code}")
                    failed_flag = True

            except Exception as e:
                logger.error(f"Error processing image {clean_url}: {e}")
                failed_flag = True

        # Update processed image URLs in the database
        product_image.output_image_urls = ",".join(output_urls)
        product_image.processed_at = timezone.now()
        product_image.save()
        product_image.output_image_urls_list = output_urls

    # Update the status of the related ImageProcessorRequest
    if failed_flag:
        image_request.status = 'failed'
        if image_request.webhook_url:
            send_webhook_notification(image_request.webhook_url, {"request_id": str(image_request.request_id), "status": "failed"})
    else:
        image_request.status = 'completed'
        if image_request.webhook_url:
            table_html = render_to_string('image_upload_table.html', {'uploads': product_images})
            send_webhook_notification(image_request.webhook_url, {"request_id": str(image_request.request_id), "status": "completed", "data": table_html})
    image_request.save()
    logger.info(f"Image processing completed for ID: {request_id}")
