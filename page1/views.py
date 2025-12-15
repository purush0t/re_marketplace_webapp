from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'base.html')

def album(request):
    return render(request, 'album_grid.html')

