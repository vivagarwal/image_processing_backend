import os
import requests
from io import BytesIO
from PIL import Image
from celery import shared_task
from django.conf import settings
from .models import ImageProcessorUpload
import logging
import uuid

logger = logging.getLogger(__name__)

# Use absolute path to ensure images are stored correctly
OUTPUT_DIR = os.path.join(os.getenv('TMP_OUTPUT_PATH'), 'processed_images')

@shared_task(bind=True)
def process_images(self, product_image_id):
    # Log current working directory for debugging
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Expected output directory: {os.path.abspath(OUTPUT_DIR)}")

    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        try:
            logger.info(f"Creating directory: {OUTPUT_DIR}")
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
    except ImageProcessorUpload.DoesNotExist:
        logger.error(f"Product image with ID {product_image_id} does not exist.")
        return

    input_urls = product_image.input_image_urls.split(',')
    output_urls = []

    for url in input_urls:
        try:
            clean_url = url.strip()
            logger.info(f"Downloading image: {clean_url}")

            response = requests.get(clean_url, stream=True)
            logger.info(f"Response is: \n{response}\n")
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                val1 = uuid.uuid4()
                output_filename = f"{product_image.product_name}_{val1}.jpg"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                # Compress and save the image
                img.save(output_path, "JPEG", quality=50)
                logger.info(f"Saved compressed image at: {output_path}")

                output_filename1 = f"{product_image.product_name}_{val1}_1.jpg"
                output_path1 = os.path.join(OUTPUT_DIR, output_filename1)
                # Compress and save the image
                img.save(output_path1, "JPEG")
                logger.info(f"Saved original image at: {output_path1}")

                # Simulate cloud upload (replace with actual cloud storage logic)
                cloud_url = f"https://example.com/uploads/{output_filename}"
                output_urls.append(cloud_url)

            else:
                logger.error(f"Failed to download image {clean_url}, HTTP status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Error processing image {clean_url}: {e}")

    # Update processed image URLs in the database
    product_image.output_image_urls = ",".join(output_urls)
    product_image.save()

    logger.info(f"Image processing completed for ID: {product_image_id}")


# @shared_task
# def process_image(image_url):
#     """ Simulate processing an image """
#     time.sleep(5)  # Simulating processing time
#     return f"Processed image: {image_url}"