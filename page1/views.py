from django.shortcuts import render, redirect, get_object_or_404
from .models import Listing, Realtor, Contact
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ListingForm, LoginForm, UserRegisterForm, ContactAgentForm
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

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

    return render(request, 'login.html', {'form': form, 'suppress_messages': True})

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
    
    # Get all unique cities in alphabetical order
    available_cities = Listing.objects.filter(is_published=True).values_list('city', flat=True).distinct().order_by('city')
    
    return render(request, 'album_grid.html', {
        'listings': listings,
        'available_cities': available_cities
    })


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
    
    # Get inquiries for this realtor's listings
    inquiries = Contact.objects.filter(
        listing__realtor=realtor
    ).order_by('-contact_date')

    return render(request, 'properties.html', {
        'form': form,
        'listings': listings,
        'inquiries': inquiries
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
    form = ContactAgentForm()
    return render(request, 'listing_detail.html', {'listing': listing, 'contact_form': form})


def contact_agent(request, id):
    """Handle contact agent form submission"""
    listing = get_object_or_404(Listing, id=id)
    
    if request.method == 'POST':
        form = ContactAgentForm(request.POST)
        if form.is_valid():
            # Create the contact record
            contact = form.save(commit=False)
            contact.listing = listing
            contact.listing_title = listing.title
            if request.user.is_authenticated:
                contact.user_id = request.user.id
            contact.save()
            
            # Prepare email content with property summary
            subject = f"New Inquiry for Property: {listing.title}"
            
            message_body = f"""
New Property Inquiry

A potential buyer has shown interest in your property listing.

--- PROPERTY DETAILS ---
Title: {listing.title}
Address: {listing.address}, {listing.city}, {listing.state} {listing.zipcode}
Price: ₹{listing.price:,}
Bedrooms: {listing.bedrooms}
Bathrooms: {listing.bathrooms}
Garage: {listing.garage}
Square Feet: {listing.sqft}
Lot Size: {listing.lot_size} acres

--- BUYER INFORMATION ---
Name: {contact.name}
Email: {contact.email}
Phone: {contact.phone}

--- MESSAGE ---
{contact.message if contact.message else '(No message provided)'}

---
To view this inquiry and respond, visit your dashboard at:
{request.build_absolute_uri(reverse('realtor_properties'))}
"""
            
            # Log email backend and addresses to help debug delivery
            try:
                backend = getattr(settings, 'EMAIL_BACKEND', 'not-set')
            except Exception:
                backend = 'error_reading'
            logger.info('Sending contact email using backend=%s from=%s to=%s', backend, getattr(settings, 'DEFAULT_FROM_EMAIL', None), listing.realtor.email)

            # Send email to the realtor
            try:
                send_mail(
                    subject=subject,
                    message=message_body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL'),
                    recipient_list=[listing.realtor.email],
                    fail_silently=False,
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Thank you! Your inquiry has been sent to the agent.'
                    })
                else:
                    messages.success(request, 'Thank you! Your inquiry has been sent to the agent.')
                    return redirect('listing_detail', id=listing.id)
            except Exception as e:
                # Log full exception for debugging
                logger.exception('Error sending contact email')

                # When in DEBUG, include the exception text in the JSON response to aid debugging
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    resp = {
                        'success': False,
                        'message': 'Error sending email. Please try again later.'
                    }
                    if getattr(settings, 'DEBUG', False):
                        resp['error'] = str(e)
                    return JsonResponse(resp, status=500)
                else:
                    # For non-AJAX, show a short message; include details when DEBUG
                    if getattr(settings, 'DEBUG', False):
                        messages.error(request, f'Error sending inquiry: {e}')
                    else:
                        messages.error(request, 'Error sending inquiry. Please try again.')
                    return redirect('listing_detail', id=listing.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, 'Please fill in all required fields.')
                return redirect('listing_detail', id=listing.id)
    
    return redirect('listing_detail', id=listing.id)



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



from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate




def return_pdf(request):
    # Generate a stylized PDF table of Contact inquiries.
    buffer = BytesIO()

    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=18)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1F4E79'))

    story = []
    story.append(Paragraph('Contacts Report', title_style))
    story.append(Spacer(1, 6))

    headers = ['ID', 'Listing', 'Name', 'Phone', 'Message', 'Date']
    data = [headers]

    # Small paragraph styles to allow wrapping inside table cells
    listing_style = ParagraphStyle('listing', parent=styles['BodyText'], fontSize=9, leading=11)
    message_style = ParagraphStyle('message', parent=styles['BodyText'], fontSize=8, leading=10)
    small_style = ParagraphStyle('small', parent=styles['BodyText'], fontSize=8, leading=10)

    contacts = Contact.objects.select_related('listing').order_by('-contact_date')[:200]
    for c in contacts:
        listing_title = c.listing_title or (c.listing.title if getattr(c, 'listing', None) else '')
        # Use Paragraphs so long text wraps instead of pushing outside page
        listing_para = Paragraph(listing_title, listing_style)
        message_text = (c.message or '')
        if len(message_text) > 200:
            message_text = message_text[:197] + '...'
        message_para = Paragraph(message_text.replace('\n', '<br/>'), message_style)
        date_str = c.contact_date.strftime('%Y-%m-%d %H:%M') if getattr(c, 'contact_date', None) else ''

        data.append([
            str(c.id),
            listing_para,
            Paragraph(c.name or '', small_style),
            Paragraph(c.phone or '', small_style),
            message_para,
            Paragraph(date_str, small_style),
        ])

    # Set column widths to fit A4 usable width (A4 width 595pt minus margins 24+24 = 547)
    # Columns: ID, Listing, Name, Phone, Message, Date
    # Widen the Phone column so numbers remain on a single line.
    table = Table(data, repeatRows=1, colWidths=[36, 110, 90, 90, 130, 91])
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4B8BBE')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'LEFT'),
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EEF3F8')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#B0BCC7')),
    ])
    table.setStyle(table_style)

    story.append(table)
    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    # Default to inline so browsers open the PDF for viewing. Append ?download=1 to force download popup.
    download = request.GET.get('download') == '1'
    disposition = 'attachment' if download else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="contacts_report.pdf"'
    return response




