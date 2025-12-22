from django.urls import path
from page1.views import album, register, logout_view, realtor_properties, login_view, featured, listing_detail

urlpatterns = [
    path('album/', album, name='album'),
    path('', featured, name='featured'),
    path('register/', register, name='register'),
    path('logout/', logout_view, name='logout_view'),
    path('properties/', realtor_properties, name='realtor_properties'),
    path('login/', login_view, name='login_view'),
    path('listing/<int:id>/', listing_detail, name='listing_detail'),
]

