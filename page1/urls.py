from django.urls import path
from page1.views import album ,home ,register,logout_view,realtor_properties,login_view

urlpatterns = [
    path('album/', album, name='album'),
    path('',home,name='home'),
    path('register/',register,name='register'),
    path('logout/',logout_view,name='logout_view'),
    path('properties/',realtor_properties, name='realtor_properties'),
    path('login/',login_view,name='login_view')
]

