from django.shortcuts import render, redirect, get_object_or_404
from .models import Listing, Realtor
from django.http import HttpResponseForbidden

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ListingForm, LoginForm, UserRegisterForm
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image

# Optional: try to import pebble for parallel resizing; fall back to ThreadPoolExecutor
try:
    from pebble import ThreadPool
    _PEBBLE_AVAILABLE = True
except Exception:
    _PEBBLE_AVAILABLE = False
    from concurrent.futures import ThreadPoolExecutor as ThreadPool





def signup(request):
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
        # Do not bind `request.FILES` to the form since we handle multiple
        # uploaded files separately. Binding files can cause validation
        # errors for FileField when using a `multiple` input.
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.realtor = realtor
            listing.save()
            
            # Handle multiple image uploads
            images = request.FILES.getlist('images')[:6]

            def resize_bytes(fileobj, max_size=(1600, 1200)):
                try:
                    img = Image.open(fileobj)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    buf = BytesIO()
                    if img.mode in ("RGBA", "LA"):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    else:
                        img = img.convert('RGB')
                    img.save(buf, format='JPEG', quality=80, optimize=True)
                    buf.seek(0)
                    return buf
                except Exception:
                    return None

            processed = []
            if images:
                # Use pebble ThreadPool for better control if available; otherwise use stdlib
                pool = ThreadPool(max_workers=4)
                if _PEBBLE_AVAILABLE:
                    map_future = pool.map(resize_bytes, images)
                    # MapFuture.result() yields the results in order
                    for idx, buf in enumerate(map_future.result()):
                        if buf:
                            name = getattr(images[idx], 'name', f'image_{idx}.jpg')
                            processed.append((name, ContentFile(buf.read())))
                    pool.close()
                    pool.join()
                else:
                    # ThreadPool from concurrent.futures behaves differently
                    with pool(max_workers=4) as ex:
                        futures = [ex.submit(resize_bytes, im) for im in images]
                        for idx, f in enumerate(futures):
                            buf = f.result()
                            if buf:
                                name = getattr(images[idx], 'name', f'image_{idx}.jpg')
                                processed.append((name, ContentFile(buf.read())))

            from .models import PropertyImage
            for idx, item in enumerate(processed):
                name, content = item
                # save the resized bytes into PropertyImage
                prop_img = PropertyImage(listing=listing, is_featured=(idx == 0))
                prop_img.image.save(name, content, save=True)
            
            messages.success(request, 'Property added successfully!')
            return redirect('realtor_properties')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
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


@login_required
def delete_property(request, id):
    # Delete a listing owned by the logged-in realtor
    if not hasattr(request.user, 'realtor_profile'):
        return HttpResponseForbidden()

    realtor = request.user.realtor_profile
    listing = get_object_or_404(Listing, id=id)
    if listing.realtor != realtor:
        return HttpResponseForbidden()

    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Property removed successfully.')
        return redirect('realtor_properties')

    # If not POST, show a simple confirm page (reuse properties template area)
    return render(request, 'confirm_delete.html', {'listing': listing})
