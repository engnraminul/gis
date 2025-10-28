from django.urls import reverse
from django.utils.html import format_html
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Profile, Backup
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# ProfileAdmin using Unfold template
@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'phone', 'email', 'user_status', 'edit_link']

    search_fields = ['user__username', 'full_name', 'email']
    ordering = ['id']
    list_filter = ['user_status']

    def edit_link(self, obj):
        # The reverse function generates the link for the profile change form
        url = reverse('admin:Login_profile_change', args=[obj.id])  # Ensure 'Login' is your app's name
        return format_html('<a href="{}">Edit</a>', url)

    edit_link.short_description = 'Edit'


# BackupAdmin using Unfold template
@admin.register(Backup)
class BackupAdmin(ModelAdmin):
    list_display = ['name', 'backup_type', 'status', 'file_size_display', 'created_at', 'created_by', 'file_exists_display']
    list_filter = ['backup_type', 'status', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    ordering = ['-created_at']
    readonly_fields = ['file_size', 'created_at', 'completed_at', 'file_exists_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'backup_type', 'status', 'description')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size', 'file_exists_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
        ('User Information', {
            'fields': ('created_by',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size_mb} MB"
        return "-"
    file_size_display.short_description = 'File Size'
    
    def file_exists_display(self, obj):
        if obj.file_exists:
            return format_html('<span style="color: green;">✓ Exists</span>')
        return format_html('<span style="color: red;">✗ Missing</span>')
    file_exists_display.short_description = 'File Status'


# Custom User Admin using Unfold template
class CustomUserAdmin(UserAdmin, ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'change_password_link')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('username', 'email')

    # Ensure the 'password' field is included in the fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),  # Password field is included
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def change_password_link(self, obj):
        # Generate the URL for the password change page
        url = reverse('admin:auth_user_password_change', args=[obj.id])  # URL for the password change page
        return format_html('<a href="{}">Change Password</a>', url)

    change_password_link.short_description = 'Change Password'

# Unregister the default User admin and register the custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
