from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Map, MapFile
from PIL import Image
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import os
from django.urls import reverse
import geopandas as gpd
from .forms import MapForm
from Login.models import Profile
from django.shortcuts import render
from django.conf import settings
import json
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.shortcuts import redirect
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.forms import modelform_factory
from django.forms import ModelForm, FileField, ClearableFileInput


def map_detail(request, map_id):
    # Fetch the map object
    map_obj = Map.objects.get(pk=map_id)
    
    # Fetch all files related to this map
    map_files = MapFile.objects.filter(map=map_obj)
    
    # Build the absolute URLs for each file
    mapfile_urls = [request.build_absolute_uri(file.file.url) for file in map_files]
    
    # Increment views count
    map_obj.views_count += 1
    map_obj.save()

    # Pass the file URLs to the template in JSON format
    context = {
        'mapfile': json.dumps(mapfile_urls),
        'map': map_obj,
    }

    return render(request, 'map/map_detail.html', context)

def home(request):
   return render(request, 'home.html') 

def shapefile(request):
    return render(request, 'layer/shapfile.html')



def map_list(request):
    # Retrieve user status if authenticated
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_status = profile.user_status
        except Profile.DoesNotExist:
            user_status = None
    else:
        user_status = None

    # Fetch published maps
    maps = Map.objects.filter(status='published').order_by('-publishing_date')

    # Set up pagination
    paginator = Paginator(maps, 6)  # 6 maps per page
    page_number = request.GET.get('page')  # Get the current page number from the query string

    try:
        paginated_maps = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer, show the first page
        paginated_maps = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range, show the last page
        paginated_maps = paginator.page(paginator.num_pages)

    # Handle form submission for map creation
    if request.method == 'POST' and request.user.is_authenticated:
        form = MapForm(request.POST, request.FILES)
        if form.is_valid():
            map_instance = form.save(commit=False)
            map_instance.user = request.user

            # Set default views_count if not set
            if not map_instance.views_count:
                map_instance.views_count = 0

            # Check user status for map approval
            if user_status not in ['administrator', 'admin']:
                map_instance.status = 'pending'
                messages.success(request, mark_safe('Your Map is <span style="color:#dc3545;">Pending</span> for Approval.'))
            else:
                map_instance.status = 'published'
                messages.success(request, mark_safe('Your Map is <span style="color:Green;">Published</span>.'))
            
            map_instance.save()

            # Handle multiple file uploads
            files = request.FILES.getlist('files[]')  # 'files[]' matches the input name in the form
            for file in files:
                map_file = MapFile(map=map_instance, file=file)
                map_file.save()

            return redirect('Login:dashboard')  # Redirect to the same page after submission
        else:
            # Show form errors for debugging
            messages.error(request, mark_safe('Your Map Submission Faileds.<br>' + str(form.errors)))
    else:
        form = MapForm()  # Empty form for GET requests
        

    # Pass maps, user status, and form to the template
    context = {
        'maps': paginated_maps,
        'user_status': user_status,
        'form': form,
    }
    return render(request, 'map/map_list.html', context)





def create_map(request):
    # Retrieve the profile and user_status only if the user is authenticated
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_status = profile.user_status
        except Profile.DoesNotExist:
            user_status = None
    else:
        user_status = None
        return HttpResponse("You don't have permission to create a map.")

    if request.method == 'POST':
        form = MapForm(request.POST, request.FILES)
        if form.is_valid():
            map_instance = form.save(commit=False)
            map_instance.user = request.user

            profile = request.user.profile
            user_status = profile.user_status
            if user_status not in ['administrator', 'admin']:
                map_instance.status = 'pending'
                messages.success(request, "Your map is pending for approval.")
            else:
                map_instance.status = 'published'
            map_instance.save()

            # Handle multiple file uploads
            files = request.FILES.getlist('files[]')  # 'files[]' should match the name attribute in the HTML form
            for file in files:
                map_file = MapFile(map=map_instance, file=file)
                map_file.save()

            return redirect('Login:dashboard')
    else:
        form = MapForm()

    return render(request, 'map/create_map.html', {'form': form, 'user_status': user_status})



@login_required
def edit_map(request, map_id):
    map_obj = get_object_or_404(Map, pk=map_id, user=request.user)
    MapEditForm = modelform_factory(Map, exclude=['user', 'status', 'views_count', 'publishing_date', 'history'])
    
    class MapFileForm(ModelForm):
        files = FileField(widget=ClearableFileInput(attrs={'multiple': True}), required=False)
        class Meta:
            model = MapFile
            fields = ['files']

    if request.method == 'POST':
        form = MapEditForm(request.POST, request.FILES, instance=map_obj)
        file_form = MapFileForm(request.POST, request.FILES)
        files_to_delete = request.POST.getlist('delete_files')
        if form.is_valid():
            form.save()
            # Delete selected files
            for file_id in files_to_delete:
                try:
                    file_obj = MapFile.objects.get(id=file_id, map=map_obj)
                    file_obj.file.delete(save=False)
                    file_obj.delete()
                except MapFile.DoesNotExist:
                    pass
            # Add new files
            for f in request.FILES.getlist('files'):
                MapFile.objects.create(map=map_obj, file=f)
            messages.success(request, "Map updated successfully.")
            return redirect('Login:dashboard')
    else:
        form = MapEditForm(instance=map_obj)
        file_form = MapFileForm()

    map_files = MapFile.objects.filter(map=map_obj)
    return render(request, 'map/edit_map.html', {
        'form': form,
        'file_form': file_form,
        'map_files': map_files,
        'map_obj': map_obj,
    })