from django.db import models
import uuid

class ImageProcessorRequest(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed')],
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} - {self.status}"


# Model to store image processing details
class ImageProcessorUpload(models.Model):
    image_processor_request = models.ForeignKey(ImageProcessorRequest, on_delete=models.CASCADE, related_name="images")
    serial_number = models.IntegerField()
    product_name = models.CharField(max_length=255)
    input_image_urls = models.TextField(help_text="Comma-separated input image URLs")
    output_image_urls = models.TextField(null=True, blank=True, help_text="Comma-separated output image URLs")
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.product_name} - {self.serial_number}"
