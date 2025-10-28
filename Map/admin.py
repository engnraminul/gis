# from django.urls import reverse
# from django.utils.html import format_html
# from django.contrib import admin
# from unfold.admin import ModelAdmin  # Ensure you have the unfold package installed
# from .models import Map, MapFile

# @admin.register(Map)
# class MapAdmin(ModelAdmin):
#     list_display = ['id',  'title', 'user', 'status', 'publishing_date', 'views_count', 'edit_link', 'detail_link']
#     search_fields = ['user__username', 'title']
#     ordering = ['publishing_date', 'id']
#     list_filter = ['status', 'publishing_date']
#     list_editable = ['status']

#     def edit_link(self, obj):
#         url = reverse('admin:Map_map_change', args=[obj.id])  # Replace 'yourapp' with your actual app name
#         return format_html('<a href="{}">Edit</a>', url)

#     edit_link.short_description = 'Edit'

#     # Method to generate detail link
#     def detail_link(self, obj):
#         # Assuming 'Map' is your app name, and 'map_detail' is the view for showing map details
#         url = reverse('Map:map_detail', kwargs={'map_id': obj.id})  # Replace 'Map' with your app name
#         return format_html('<a href="{}" target="_blank">Preview</a>', url)

#     detail_link.short_description = 'Map Preview'


# @admin.register(MapFile)
# class MapFileAdmin(ModelAdmin):
#     list_display = ['id', 'map', 'file']
#     search_fields = ['map__title']
#     ordering = ['id']


from django.urls import reverse
from django.utils.html import format_html
from django.contrib import admin
from unfold.admin import ModelAdmin  # Ensure you have the unfold package installed
from .models import Map, MapFile, MapColor


class MapFileInline(admin.TabularInline):  # You can also use StackedInline for a different layout
    model = MapFile
    extra = 1  # Number of empty file fields to display for adding new files

class MapColorInline(admin.TabularInline):  # You can also use StackedInline for a different layout
    model = MapColor
    extra = 1  # Number of empty file fields to display for adding new files


@admin.register(Map)
class MapAdmin(ModelAdmin):
    #icon = 'fas fa-globe'
    list_display = ['id', 'title', 'user', 'status', 'publishing_date', 'views_count', 'edit_link', 'detail_link', 'status_badge']
    search_fields = ['user__username', 'title']
    ordering = ['-publishing_date']
    list_filter = ['status', 'publishing_date']  # Dropdown filter for status
    list_editable = ['status']
    

    inlines = [MapFileInline, MapColorInline]
    

    def status(self, obj):
        return format_html('<span>{}</span>', obj.status)

    status.short_description = 'Status Action'  # Ensure this is correctly set

    def edit_link(self, obj):
        url = reverse('admin:Map_map_change', args=[obj.id])  # Replace 'yourapp' with your actual app name
        return format_html('<a href="{}">Edit</a>', url)

    edit_link.short_description = 'Edit'

    # Method to generate detail link
    def detail_link(self, obj):
        url = reverse('Map:map_detail', kwargs={'map_id': obj.id})  # Replace 'Map' with your app name
        return format_html('<a href="{}" target="_blank">Preview</a>', url)

    detail_link.short_description = 'Map Preview'

    # Method to display status badge
    def status_badge(self, obj):
        if obj.status == 'pending':
            return format_html('<span style="color: white; background-color: orange; padding: 4px; border-radius: 3px;">Pending</span>')
        elif obj.status == 'reject':
            return format_html('<span style="color: white; background-color: red; padding: 4px; border-radius: 3px;">Rejected</span>')
        elif obj.status == 'published':
            return format_html('<span style="color: white; background-color: green; padding: 4px; border-radius: 3px;">Published</span>')
        else:
            return format_html('<span style="color: white; background-color: gray; padding: 4px; border-radius: 3px;">{}</span>', obj.status)

    status_badge.short_description = 'Status'
    



