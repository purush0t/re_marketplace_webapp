from django.urls import path
from page1.views import album ,home

urlpatterns = [
    path('album/', album, name='album'),
    path('',home,name='home'),
]

