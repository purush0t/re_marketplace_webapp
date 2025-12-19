from django.contrib import admin
from .models import Realtor, Listing, Contact

# Register your models here.



@admin.register(Realtor)
class RealtorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'is_mvp')
    search_fields = ('name', 'email')
    list_filter = ('is_mvp',)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'city', 'state', 'is_published')
    list_filter = ('city', 'state', 'is_published')
    search_fields = ('title', 'address', 'city', 'state')
    list_editable = ('is_published',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'listing_title', 'email', 'contact_date')
    search_fields = ('name', 'email', 'listing_title')