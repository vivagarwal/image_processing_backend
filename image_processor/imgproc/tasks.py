import os
import requests
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.conf import settings
from .models import ImageProcessorUpload
import logging
import uuid
import boto3
from botocore.exceptions import NoCredentialsError
from django.utils import timezone

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
    # bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    bucket_name = None

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

@shared_task(bind=True)
def process_images(self, product_image_id):
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
    logger.info(f"Processing image with ID: {product_image_id}")
    try:
        product_image = ImageProcessorUpload.objects.get(id=product_image_id)
        product_image.image_processor_request.status = 'processing'
        product_image.image_processor_request.save()
    except ImageProcessorUpload.DoesNotExist:
        logger.error(f"Product image with ID {product_image_id} does not exist.")
        product_image.image_processor_request.status = 'failed'
        failed_flag = True
        product_image.image_processor_request.save()
        return

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
                    product_image.image_processor_request.status = 'failed'
                    failed_flag = True
                    product_image.image_processor_request.save()
            else:
                logger.error(f"Failed to download image {clean_url}, HTTP status code: {response.status_code}")
                product_image.image_processor_request.status = 'failed'
                failed_flag = True
                product_image.image_processor_request.save()

        except Exception as e:
            logger.error(f"Error processing image {clean_url}: {e}")
            product_image.image_processor_request.status = 'failed'
            failed_flag = True
            product_image.image_processor_request.save()

    # Update processed image URLs in the database
    product_image.output_image_urls = ",".join(output_urls)
    product_image.processed_at = timezone.now()
    product_image.save()

    # Update the status of the related ImageProcessorRequest
    if product_image.image_processor_request and not failed_flag:
        product_image.image_processor_request.status = 'completed'
        product_image.image_processor_request.save()
        logger.info(f"Updated processing status to 'completed' for request ID: {product_image.image_processor_request.request_id}")

    logger.info(f"Image processing completed for ID: {product_image_id}")
