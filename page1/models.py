from django.db import models
from django.contrib.auth.models import User
from io import BytesIO
import os
from django.core.files.base import ContentFile
from PIL import Image


def property_image_upload_path(instance, filename):
    """Upload path: property_images/listing_<id>/<filename>

    Assumes `instance.listing` is set and listing.pk exists (our flow saves
    the listing before creating PropertyImage)."""
    listing_id = getattr(instance.listing, 'id', None) or 'unknown'
    return f'property_images/listing_{listing_id}/{filename}'
# Create your models here.
class Realtor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
     related_name='realtor_profile'
    )
    name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='', blank=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    is_mvp = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Listing(models.Model):
    realtor = models.ForeignKey(
        Realtor,
        on_delete=models.CASCADE,
        related_name='listings'
    )
    title = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    garage = models.IntegerField()
    sqft = models.IntegerField()
    lot_size = models.DecimalField(max_digits=5, decimal_places=2)
    photo_main = models.ImageField(upload_to='',blank=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    list_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PropertyImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to=property_image_upload_path)
    caption = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'created_at']

    def __str__(self):
        return f"Image for {self.listing.title}"

    def save(self, *args, **kwargs):
        """Save and resize the image to reasonable dimensions to save space.

        This opens the saved image (FieldFile), creates a resized version
        and writes it back to the same field. Works with local storage
        (development)."""
        # First save to ensure `self.image.path` is available
        super().save(*args, **kwargs)

        try:
            img_path = self.image.path
        except Exception:
            # If storage backend doesn't provide a local path, bail out
            return

        try:
            img = Image.open(img_path)
            max_size = (1600, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Prepare buffer and save optimized image
            buffer = BytesIO()
            fmt = 'JPEG'
            if img.mode in ("RGBA", "LA"):
                # Convert images with alpha to RGB with white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')

            img.save(buffer, format=fmt, quality=80, optimize=True)
            buffer.seek(0)

            # Replace the image file without changing the name
            name = os.path.basename(self.image.name)
            self.image.save(name, ContentFile(buffer.read()), save=False)
            buffer.close()

            # Final save to update any DB fields
            super().save(update_fields=['image'])
        except Exception:
            # If anything goes wrong, don't crash the request — keep original image
            return


class Contact(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    listing_title = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    user_id = models.IntegerField(blank=True, null=True)
    contact_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.listing_title}"