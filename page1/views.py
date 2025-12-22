from django.shortcuts import render, redirect, get_object_or_404
from .models import Listing, Realtor

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ListingForm, LoginForm, UserRegisterForm





def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )

            if form.cleaned_data['is_realtor']:
                Realtor.objects.create(
                    user=user,
                    name=user.username,
                    email=user.email,
                    phone=''
                )
            return redirect('login_view')  # or home
    else:
        form = UserRegisterForm()

    return render(request, 'register.html', {'form': form})




def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(email=form.cleaned_data['email'])
                user = authenticate(
                    request,
                    username=user.username,
                    password=form.cleaned_data['password']
                )
                if user:
                    login(request, user)
                    return redirect('featured')  # or another page
                else:
                    messages.error(request, 'Invalid email or password')
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login_view')




# Create your views here.


def album(request):
    listings = Listing.objects.filter(is_published=True).order_by('-list_date')
    
    # Filter by keyword
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        listings = listings.filter(title__icontains=keyword)
    
    # Filter by city
    if 'city' in request.GET:
        city = request.GET['city']
        listings = listings.filter(city__icontains=city)
    
    # Filter by bedrooms
    if 'bedrooms' in request.GET and request.GET['bedrooms']:
        bedrooms = int(request.GET['bedrooms'])
        listings = listings.filter(bedrooms__gte=bedrooms)
    
    # Filter by max price
    if 'max_price' in request.GET and request.GET['max_price']:
        max_price = int(request.GET['max_price'])
        listings = listings.filter(price__lte=max_price)
    
    return render(request, 'album_grid.html', {'listings': listings})


def featured(request):
    """Display featured properties and latest listings"""
    featured_listings = Listing.objects.filter(
        is_published=True, 
        is_featured=True
    ).order_by('-list_date')[:6]  # Limit to 6 featured properties
    
    latest_listings = Listing.objects.filter(
        is_published=True
    ).order_by('-list_date')[:9]  # Limit to 9 latest properties
    
    return render(request, 'featured.html', {
        'featured_listings': featured_listings,
        'latest_listings': latest_listings
    })



@login_required
def realtor_properties(request):
    #  Block non-realtors
    if not hasattr(request.user, 'realtor_profile'):
        return redirect('featured')

    realtor = request.user.realtor_profile

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.realtor = realtor
            listing.save()
            
            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            for idx, image in enumerate(images[:6]):  # Limit to 6 images
                from .models import PropertyImage
                PropertyImage.objects.create(
                    listing=listing,
                    image=image,
                    is_featured=(idx == 0)  # First image as featured
                )
            
            messages.success(request, 'Property added successfully!')
            return redirect('realtor_properties')
    else:
        form = ListingForm()

    listings = Listing.objects.filter(realtor=realtor).order_by('-list_date')

    return render(request, 'properties.html', {
        'form': form,
        'listings': listings
    })



def listings(request):
    qs = Listing.objects.filter(is_published=True)

    keyword = request.GET.get('keyword')
    city = request.GET.get('city')
    bedrooms = request.GET.get('bedrooms')
    max_price = request.GET.get('max_price')

    if keyword:
        qs = qs.filter(title__icontains=keyword)

    if city:
        qs = qs.filter(city__icontains=city)

    if bedrooms:
        qs = qs.filter(bedrooms__gte=bedrooms)

    if max_price:
        qs = qs.filter(price__lte=max_price)

    return render(request, 'album_grid.html', {
        'listings': qs
    })


def listing_detail(request, id):
    listing = get_object_or_404(Listing, id=id)
    return render(request, 'listing_detail.html', {'listing': listing})
