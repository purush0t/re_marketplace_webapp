from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Realtor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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
        on_delete=models.DO_NOTHING,
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
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1)
    garage = models.IntegerField()
    sqft = models.IntegerField()
    lot_size = models.DecimalField(max_digits=5, decimal_places=2)
    photo_main = models.ImageField(upload_to='')
    is_published = models.BooleanField(default=True)
    list_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


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