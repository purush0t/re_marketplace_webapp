from django.urls import path
from page1.views import album, signup, logout_view, realtor_properties, login_view, featured, listing_detail, delete_property, contact_agent

urlpatterns = [
    path('album/', album, name='album'),
    path('', featured, name='featured'),
    path('signup/', signup, name='signup'),
    path('logout/', logout_view, name='logout_view'),
    path('properties/', realtor_properties, name='realtor_properties'),
    path('properties/delete/<int:id>/', delete_property, name='delete_property'),
    path('login/', login_view, name='login_view'),
    path('listing/<int:id>/', listing_detail, name='listing_detail'),
    path('listing/<int:id>/contact/', contact_agent, name='contact_agent'),
]


