from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Map, MapFile
from PIL import Image
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import os
from django.urls import reverse
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
#import geopandas as gpd
import folium
from .forms import MapForm
from Login.models import Profile
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage



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
    paginator = Paginator(maps, 8)  # 6 maps per page
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
            messages.success(request, mark_safe('Your Map Submittion is Failed.'))
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



def edit_map(request, map_id):
    # Retrieve the profile and user_status only if the user is authenticated
    if not request.user.is_authenticated:
        return HttpResponse("You need to be logged in to edit a map.")
    
    try:
        profile = request.user.profile
        user_status = profile.user_status
    except Profile.DoesNotExist:
        return HttpResponse("You don't have permission to edit a map.")

    map_instance = get_object_or_404(Map, pk=map_id)
    history = map_instance.history.all()
    

    # Check if the current user has permission to edit this map
    if map_instance.user != request.user:
        return HttpResponse("You don't have permission to edit this map.")
    
    if request.method == 'POST':
        form = MapForm(request.POST, request.FILES, instance=map_instance)
        if form.is_valid():
            map_instance = form.save(commit=False)

            delete_files = request.POST.getlist('delete_files')
            for file_id in delete_files:
                map_file = MapFile.objects.get(id=file_id)
                map_file.file.delete()  # Delete file from storage
                map_file.delete()  # Delete file instance from database
            # Update the status based on user status
            if user_status not in ['administrator', 'admin']:
                map_instance.status = 'review'
                messages.success(request, "Your map is pending for approval.")
            else:
                map_instance.status = 'published'

            map_instance.save()

            # Handle multiple file uploads
            files = request.FILES.getlist('files[]')  # 'files[]' should match the name attribute in the HTML form
            for file in files:
                map_file = MapFile(map=map_instance, file=file)
                map_file.save()

            messages.success(request, "Map successfully updated.")
            return redirect('Map:map_list')
    else:
        form = MapForm(instance=map_instance)

    return render(request, 'map/edit_map.html', {'form': form, 'map_instance': map_instance, 'user_status': user_status, 'history': history,})







import os
import zipfile
import folium
import geopandas as gpd
from django.core.files.storage import default_storage
from django.shortcuts import render
from .models import Map, MapFile, MapColor
import pandas as pd
import logging
from folium.plugins import Draw
import json
from folium.plugins import MeasureControl
from weasyprint import HTML
from branca.element import MacroElement, Element
from jinja2 import Template
import tempfile
import shutil
from folium.plugins import MarkerCluster
from shapely import wkt
import simplekml






logger = logging.getLogger(__name__)

def convert_kml_to_geojson(kml_file_path):
    """Convert KML file to GeoJSON using geopandas."""
    try:
        gdf = gpd.read_file(kml_file_path)
        geojson_file_path = kml_file_path.replace('.kml', '.geojson')
        gdf.to_file(geojson_file_path, driver='GeoJSON')
        return geojson_file_path
    except Exception as e:
        logger.error(f'Error converting KML to GeoJSON: {str(e)}')
    return None

def read_kmz(file_path):
    """Extracts KML from a KMZ file and returns the path to the KML file."""
    try:
        with zipfile.ZipFile(file_path, 'r') as kmz:
            for filename in kmz.namelist():
                if filename.endswith('.kml'):
                    logger.info(f'Extracting KML from {filename}')
                    kml_path = os.path.join(os.path.dirname(file_path), filename)
                    with kmz.open(filename) as kml_file:
                        with open(kml_path, 'wb') as output_file:
                            output_file.write(kml_file.read())
                    return kml_path
    except Exception as e:
        logger.error(f'Error reading KMZ file {file_path}: {str(e)}')
    return None

import random

def random_color():
    """Generate a random color in hex format."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def map_detail(request, map_id):
    map_obj = Map.objects.get(pk=map_id)
    mapfiles = MapFile.objects.filter(map=map_obj)
    mapcolors = MapColor.objects.filter(map=map_obj)

    # Create a Folium map object
    m = folium.Map(location=(23.999941, 90.420273), zoom_start=12)
    folium.TileLayer('openstreetmap', min_zoom=3, max_zoom=18).add_to(m)

    folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Tiles &copy; Esri',
    name='World Street Map'  # This is the name displayed in the LayerControl
    ).add_to(m)
    
    folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        # overlay = True,
        # control = True
       ).add_to(m)
    
    # Google Satellite Tile Layer (if needed)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        #overlay=True,
        control=True
    ).add_to(m)
    
    m.add_child(MeasureControl())
 
    # Add the Draw plugin
    draw = Draw(export=True)
    draw.add_to(m)

   
    # Create a Layer control and initialize legend colors
    layer_control = folium.LayerControl()
    legend = {}  # Store colors for each map file
    legend_kmz={}

    folium.plugins.LocateControl().add_to(m)

    legend_html = '''
    <div style="position: fixed; bottom: 30px; left: 20px; background-color: white; 
                padding: 10px; z-index: 9999; font-family: Arial, sans-serif; 
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); max-height: 400px; overflow-y: auto;">
        <h4>Legend</h4>
        <ul style="list-style-type: none; padding-left: 0; margin: 0;">
        '''


    mapcolors_iter = iter(mapcolors)  # Create an iterator for mapcolors

    # Processing map files
    for mapfile in mapfiles:
        # Try to get the next color from the mapcolors iterator
        try:
            mapcolor = next(mapcolors_iter)  # Get the next MapColor
            color = mapcolor.color if mapcolor and mapcolor.color else random_color()  # Use the color from MapColor, or generate a random color if missing
        except StopIteration:
            # If we've exhausted all MapColors, generate a random color
            color = random_color()

        file_path = default_storage.path(mapfile.file.name)
        file_extension = file_path.split('.')[-1].lower()

        # Now you have a color (either random or from the MapColor)
        file_path = default_storage.path(mapfile.file.name)
        file_extension = file_path.split('.')[-1].lower()
            
        file_name = os.path.basename(mapfile.file.name).split('.')[0]  # Get only the file name without path or extension
        legend[file_name] = color  # Store color for legend
        feature_group = folium.FeatureGroup(name=file_name)
        marker_cluster = MarkerCluster().add_to(feature_group)

        if file_extension == 'geojson':
            # Load and add GeoJSON data
            with open(file_path) as f:
                geojson_data = json.load(f)

            if geojson_data:
                # Use the legend color for all geometry types within this file
                geometry_color = color  # Use the legend color for all geometries

                # Track geometry groups by file and geometry type
                geometry_groups = {}

                # Process each feature, grouping by both file name and geometry type
                for feature in geojson_data['features']:
                    geometry_type = feature['geometry']['type']
                    if geometry_type == 'Point':
                        # Handle Point geometry by adding markers directly
                        coords = feature['geometry']['coordinates']
                        properties = feature.get('properties', {})

                        # Create popup content
                        # Create popup content
                        popup_content = '''
                            <div style="width: 100%; max-width: 400px; font-family: inter, sans-serif; max-height: 450px; ">
                                <table style="width: 100%;">'''

                        for key, value in properties.items():
                            popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'

                        popup_content += '</table></div>'

                        # Create the popup with a fixed width and dynamic content height using CSS overflow
                        popup = folium.Popup(
                            folium.IFrame(
                                html=popup_content,
                                width=400,  # Fixed width constraint
                                height=300  # Base height for the popup content
                            ),
                            max_width=400  # Set max width for the popup
                        )

                        # Add CircleMarker for the Point geometry
                        lat, lon = coords[1], coords[0]
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            color=geometry_color,
                            fill=True,
                            fill_color=geometry_color,
                            fill_opacity=0.6,
                            popup=popup
                        ).add_to(marker_cluster)

                    else:
                        # For non-point geometries, group them for GeoJSON layer addition
                        layer_name = f"{file_name} - {geometry_type}"

                        if layer_name not in geometry_groups:
                            geometry_groups[layer_name] = []

                        geometry_groups[layer_name].append(feature)

                # Add separate GeoJSON layers for each geometry type with the same color as in legend
                for layer_name, features in geometry_groups.items():
                    geojson_layer = folium.FeatureGroup(
                        name=f'<span style="color: {geometry_color};">{layer_name}</span>'
                    )

                    for feature in features:
                        properties = feature.get('properties', {})

                        # Create popup content for the individual feature
                        popup_content = '''
                            <div style="width: 100%; max-width: 400px; font-family: inter, sans-serif; max-height: 400px; overflow-y: auto;">
                                <table style="width: 100%;">'''

                        for key, value in properties.items():
                            popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'

                        popup_content += '</table></div>'

                        # Create the popup without setting a fixed height on the IFrame
                        popup = folium.Popup(
                            folium.IFrame(
                                html=popup_content,
                                width=400  # Only set width, remove height to allow CSS-based height control
                            ),
                            max_width=400  # Set max width for the popup
                        )

                        # Create a GeoJson object for each feature with its own popup
                        folium.GeoJson(
                            feature,
                            style_function=lambda x, color=geometry_color: {'color': color, 'weight': 4},
                            highlight_function=lambda x: {'weight': 3, 'color': 'orange'},
                            popup=popup
                        ).add_to(geojson_layer)

                    geojson_layer.add_to(feature_group)

                # Add feature group to map
                feature_group.add_to(m)

                   
        if file_extension == 'zip':
            # Generate a unique random color for this file
            #color = random_color()  # Generate a new color for each file
            file_name = os.path.basename(file_path).replace('.zip', '')

            # Create a unique temporary directory for each zip file extraction
            with tempfile.TemporaryDirectory() as extraction_dir:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extraction_dir)

                # Process shapefiles as before
                extracted_files = os.listdir(extraction_dir)
                shapefile_name = [f for f in extracted_files if f.endswith('.shp')]

                if shapefile_name:
                    shapefile_path = os.path.join(extraction_dir, shapefile_name[0])
                    gdf = gpd.read_file(shapefile_path)
                    if gdf.crs != "EPSG:4326":
                        gdf = gdf.to_crs("EPSG:4326")
                    
                    if gdf.empty:
                        print("The GeoDataFrame is empty. Please check the shapefile.")
                    else:
                        # Generate custom popup content for each feature
                        for _, row in gdf.iterrows():
                            properties = row.to_dict()  # Convert the row to a dictionary
                            
                            # Generate the popup content dynamically
                            popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                            row_index = 0  # Track the row index to alternate colors

                            for key, value in properties.items():
                                if key not in ['geometry', 'other_geom_column_if_any']:  # Exclude unwanted keys
                                    # Determine cell color based on even/odd row index for value cells only
                                    value_cell_color = '#f2f2f2' if row_index % 2 == 0 else '#ffffff'
                                    
                                    popup_content += (
                                        f'<tr>'
                                        f'<td><strong>{key}:</strong></td>'
                                        f'<td style="background-color: {value_cell_color};">{value}</td>'
                                        f'</tr>'
                                    )
                                    
                                    row_index += 1  # Increment row index for alternating color in value cells

                            popup_content += '</table>'

                            # Estimate popup height based on the number of rows (each row estimated at 30px height)
                            estimated_height = min(450, 30 * row_index)  # Max height of 450px
                            popup_width = 400  # Max width of 400px

                            # Create the popup with estimated height and max width
                            popup = folium.Popup(
                                folium.IFrame(
                                    html=popup_content,
                                    width=popup_width,
                                    height=estimated_height
                                ),
                                max_width=popup_width
                            )

                            
                            if row.geometry.type == 'Point':
                                lat, lon = row.geometry.y, row.geometry.x
                                folium.CircleMarker(
                                    location=[lat, lon],
                                    radius=8,
                                    color=color,  # You can assign color as needed
                                    fill=True,
                                    fill_color=color,
                                    fill_opacity=0.6,
                                    popup=popup,
                                ).add_to(marker_cluster)

                            elif row.geometry.type == 'LineString':
                                lat_lon_list = [(coord[1], coord[0]) for coord in row.geometry.coords if len(coord) >= 2]
                                folium.PolyLine(
                                    locations=lat_lon_list,
                                    color=color,
                                    weight=3,
                                    opacity=0.7,
                                    popup=popup,
                                ).add_to(feature_group)

                            elif row.geometry.type == 'Polygon':
                                lat_lon_list = [(coord[1], coord[0]) for coord in row.geometry.exterior.coords if len(coord) >= 2]
                                folium.Polygon(
                                    locations=lat_lon_list,
                                    color=color,
                                    fill=True,
                                    fill_color=color,
                                    fill_opacity=0.3,
                                    popup=popup,
                                ).add_to(feature_group)

                            elif row.geometry.type.startswith('Multi'):
                                for geom in row.geometry.geoms:
                                    if geom.type == 'Point':
                                        lat, lon = geom.y, geom.x
                                        folium.CircleMarker(
                                            location=[lat, lon],
                                            radius=8,
                                            color=color,
                                            fill=True,
                                            fill_color=color,
                                            fill_opacity=0.6,
                                            popup=folium.Popup(f"Coordinates: ({lat}, {lon})"),
                                        ).add_to(feature_group)

                                    elif geom.type == 'LineString':
                                        lat_lon_list = [(coord[1], coord[0]) for coord in geom.coords if len(coord) >= 2]
                                        folium.PolyLine(
                                            locations=lat_lon_list,
                                            color=color,
                                            weight=3,
                                            opacity=0.7,
                                        ).add_to(feature_group)

                                    elif geom.type == 'Polygon':
                                        lat_lon_list = [(coord[1], coord[0]) for coord in geom.exterior.coords if len(coord) >= 2]
                                        folium.Polygon(
                                            locations=lat_lon_list,
                                            color=color,
                                            fill=True,
                                            fill_color=color,
                                            fill_opacity=0.3,
                                        ).add_to(feature_group)

        if file_extension == 'csv':
            try:
                df = pd.read_csv(file_path)

                # Check if the columns `lat` and `lng` exist
                if 'lat' in df.columns and 'lng' in df.columns:
                    for _, row in df.iterrows():
                        lat = row['lat']
                        lon = row['lng']

                        # Create custom properties for the popup
                        properties = row.to_dict()  # Convert the row to a dictionary

                        # Generate custom popup content
                        popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                        for key, value in properties.items():
                            popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                        popup_content += '</table>'

                        # Create the folium Popup with IFrame
                        popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                        # Create and add a CircleMarker to the map
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=5,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.6,
                            popup=popup
                        ).add_to(feature_group)

                # Check if the columns `lat` and `lon` exist
                elif 'lat' in df.columns and 'lon' in df.columns:
                    for _, row in df.iterrows():
                        lat = row['lat']
                        lon = row['lon']

                        # Create custom properties for the popup
                        properties = row.to_dict()  # Convert the row to a dictionary

                        # Generate custom popup content
                        popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                        for key, value in properties.items():
                            popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                        popup_content += '</table>'

                        # Create the folium Popup with IFrame
                        popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                        # Create and add a CircleMarker to the map
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.6,
                            popup=popup
                        ).add_to(feature_group)

                # Check if the columns `Lat_Y` and `Long_X` exist
                elif 'Lat_Y' in df.columns and 'Long_X' in df.columns:
                    for _, row in df.iterrows():
                        lat = row['Lat_Y']
                        lon = row['Long_X']

                        # Create custom properties for the popup
                        properties = row.to_dict()  # Convert the row to a dictionary

                        # Generate custom popup content
                        popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                        for key, value in properties.items():
                            popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                        popup_content += '</table>'

                        # Create the folium Popup with IFrame
                        popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                        # Create and add a CircleMarker to the map
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.6,
                            popup=popup
                        ).add_to(marker_cluster)

                # Check if `WKT` column exists to parse POINT data
                elif 'WKT' in df.columns:
                    for _, row in df.iterrows():
                        if row['WKT'].startswith("POINT"):
                            point = wkt.loads(row['WKT'])
                            lat, lon = point.y, point.x

                            # Create custom properties for the popup
                            properties = row.to_dict()  # Convert the row to a dictionary

                            # Generate custom popup content
                            popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                            for key, value in properties.items():
                                popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                            popup_content += '</table>'

                            # Create the folium Popup with IFrame
                            popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                            # Create and add a CircleMarker to the map
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=8,
                                color=color,
                                fill=True,
                                fill_color=color,
                                fill_opacity=0.6,
                                popup=popup
                            ).add_to(marker_cluster)
                else:
                    logger.warning("CSV file does not contain valid latitude and longitude columns.")

            except Exception as e:
                logger.error(f'Error reading CSV file {file_path}: {str(e)}')

        if file_extension == 'kmz':
            file_name = os.path.basename(file_path).replace('.kmz', '')
            if file_name not in legend_kmz:
                legend_kmz[file_name] = color
            try:
                kml_path = read_kmz(file_path)
                # color=random_color()
                # legend_kmz[file_name] = color
                if kml_path:
                    geojson_path = convert_kml_to_geojson(kml_path)
                    if geojson_path:
                        with open(geojson_path) as f:
                            geojson_data = json.load(f)

                        # Generate a random color for the current file
                        geometry_color = color
                        # Process features for CircleMarker
                        
                        for feature in geojson_data['features']:
                            geometry_type = feature['geometry']['type']
                            coords = feature['geometry']['coordinates']
                            properties = feature.get('properties', {})

                            # Create a popup for properties for Points
                            popup_content = '<table style="width: 100%;">'
                            for key, value in properties.items():
                                popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                            popup_content += '</table>'
                            popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                            if geometry_type == 'Point':
                                lat, lon = coords[1], coords[0]  # GeoJSON coordinates are [lon, lat]
                                folium.CircleMarker(
                                    location=[lat, lon],
                                    radius=8,  # Adjust radius as needed
                                    color=geometry_color,
                                    fill=True,
                                    fill_color=geometry_color,
                                    fill_opacity=0.6,
                                    popup=popup  # Add HTML popup for points
                                ).add_to(marker_cluster)

                        # Group non-point features and add them as GeoJSON layers
                        geometry_groups = {}
                        colors = {}

                        # Process each feature, grouping by both file name and geometry type
                        for feature in geojson_data['features']:
                            if feature['geometry']['type'] != 'Point':
                                geometry_type = feature['geometry']['type']
                                file_name = os.path.basename(geojson_path).split('.')[0]  # Extract filename without extension
                                layer_name = f"{file_name} - {geometry_type}"  # Unique layer name by file and geometry type

                                if layer_name not in geometry_groups:
                                    geometry_groups[layer_name] = []
                                    colors[layer_name] = color  # Assign a unique color to each file's geometry type

                                geometry_groups[layer_name].append(feature)

                        # Add separate GeoJSON layers for each geometry type with unique colors
                        for layer_name, features in geometry_groups.items():
                            color = colors[layer_name]

                            geojson_layer = folium.FeatureGroup(
                                name=f'<span style="color: {color};">{layer_name}</span>'
                            )

                            for feature in features:
                                properties = feature.get('properties', {})

                                # Create popup content for the individual feature
                                popup_content = '<table style="width: 100%; font-family: inter, sans-serif">'
                                for key, value in properties.items():
                                    popup_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
                                popup_content += '</table>'
                                popup = folium.Popup(folium.IFrame(html=popup_content, width=400, height=450), parse_html=True)

                                # Create a GeoJson object for each feature with its own popup
                                folium.GeoJson(
                                    feature,
                                    style_function=lambda x, color=color: {'color': color, 'weight': 2},
                                    highlight_function=lambda x: {'weight': 3, 'color': 'orange'},
                                    popup=popup
                                ).add_to(geojson_layer)

                            geojson_layer.add_to(feature_group)

            except Exception as e:
                print(f"Error processing file {file_path}: {e}")




        
        # Add the feature group to the map
        feature_group.add_to(m)

        # Add to global legend HTML
    for file_name, color in legend.items():
        legend_html += f'''
                <li>
                    <span style="background-color: {color}; width: 12px; height: 12px;
                                display: inline-block; margin-right: 5px;"></span>
                    {file_name}
                </li>
            '''



    legend_html += '</ul></div>'

    # Add the global legend to the map
    m.get_root().html.add_child(folium.Element(legend_html))
    # Add the layer control to the map
    layer_control.add_to(m)

    # Step 2: Add the Draw control with export enabled
   

    export_js = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.4.0/jspdf.umd.min.js"></script>
<script>
    function saveAsPDF() {
        html2canvas(document.querySelector("#map")).then(canvas => {
            var imgData = canvas.toDataURL("image/png");
            var pdf = new jspdf.jsPDF("landscape", "pt", [canvas.width, canvas.height]);
            pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
            pdf.save("map.pdf");
        });
    }

    function printMap() {
        window.print();
    }

    window.onload = function() {
        // Delay to ensure elements exist before adding tooltip
        setTimeout(function() {
            // Add tooltip to the export button
            var exportButton = document.querySelector('a#export');
            if (exportButton) {
                exportButton.setAttribute('title', 'Export Drawing');  // Tooltip text
            }

            // Add tooltip to the print button
            var printButton = document.querySelector('.print-btn');
            if (printButton) {
                printButton.setAttribute('title', 'Save or Print PDF');  // Tooltip text
            }
        }, 10);  // Delay in milliseconds (adjust if needed)
    };
</script>

<!-- PDF and Print Buttons -->
<div class="print-btn" style="position: absolute; top: 180px; right: 5px; z-index: 1000; font-family: helvitica neue;">
    <button onclick="printMap()" style="padding: 8px 8px; margin: 5px; background-color: transparent; color: transparent; border: none; cursor: pointer; border-radius: 5px;">Print</button>
</div>

"""

    custom_css = """
<link rel="stylesheet" type="text/css" href="/static/css/folium.css">
<style>
a.leaflet-control-measure-toggle.js-toggle {
    background-image: url(https://gis.vnode.digital/media/icon/scale-icon.png)!important;
    background-size: contain!important;
}
a.leaflet-control-layers-toggle {
    background-image: url(https://gis.vnode.digital/media/icon/layers-icon.png) !important;
    background-size: contain !important;
    width: 43px!important;
    height: 44px;
}
a#export {
    background-image: url(https://gis.vnode.digital/media/icon/export-icon.png) !important;
    background-size: contain !important;
    color: transparent;
    background-size: contain;
    background-repeat: no-repeat;
    width: 44px;
    height: 43px;
    right:12px!important;
}

.print-btn {
    background-image: url(https://gis.vnode.digital/media/icon/print-icon.png) !important;
    background-size: contain !important;
    color: transparent;
    background-size: contain;
    background-repeat: no-repeat;
    width: 44px;
    height: 44px;
    background-color: transparent!important;
    color: transparent!important;
    border-radius: 5px;
    right:12px!important;
}
.leaflet-touch .leaflet-bar a {
    width: 29px!important;
    height: 30px;
}

a.leaflet-bar-part.leaflet-bar-part-single {
    background-image: url(https://gis.vnode.digital/media/icon/Current-location.png)!important;
    background-size: contain;
    color: transparent;
}s
</style>
"""
    # Add the CSS to the map
    m.get_root().html.add_child(folium.Element(custom_css))

    # Add JavaScript and buttons to the map
    m.get_root().html.add_child(folium.Element(export_js))

    # Step 3: Save the map to an HTML file
    html_file = 'map_with_buttons.html'
    m.save(html_file)

    # Convert Folium map to HTML
   
    map_html = m._repr_html_()
    
    context = {
        'map_html': map_html,
        'map_id': map_id,
    }
    return render(request, 'map/folium_map.html', context)



