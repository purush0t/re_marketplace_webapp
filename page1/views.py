from django.shortcuts import render, redirect
from .models import Listing,Realtor

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.contrib.auth.decorators import login_required
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
                    return redirect('home')
            except User.DoesNotExist:
                pass
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login_view')




# Create your views here.
def home(request):
    return render(request, 'base.html')

def album(request):
    return render(request, 'album_grid.html')



@login_required
def realtor_properties(request):
    #  Block non-realtors
    if not hasattr(request.user, 'realtor_profile'):
        return redirect('home')

    realtor = request.user.realtor_profile

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.realtor = realtor
            listing.save()
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

    if request.GET.get('city'):
        qs = qs.filter(city__icontains=request.GET['city'])

    if request.GET.get('max_price'):
        qs = qs.filter(price__lte=request.GET['max_price'])

    return render(request, 'listings/grid.html', {
        'listings': qs
    })