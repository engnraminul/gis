from django.db import models
from django.contrib.auth.models import User
import os


# class User(models.Model):
#     username = models.CharField(max_length=100, unique=True)
#     # password = models.CharField(max_length=100)
#     # email = models.EmailField(unique=True)


class Profile(models.Model):
    USER_STATUS_CHOICES = (
        ('administrator', 'Administrator'),
        ('admin', 'Admin'),
        ('user', 'User'),

    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    user_status = models.CharField(max_length=20, choices=USER_STATUS_CHOICES, default='user')

    def __str__(self):
        return self.user.username
    
    def save(self, *args, **kwargs):
        if not self.email:  # If email is not provided, set it to the email of the associated user
            self.email = self.user.email
        super().save(*args, **kwargs)


class Backup(models.Model):
    BACKUP_TYPE_CHOICES = (
        ('database', 'Database Only'),
        ('media', 'Media Files Only'),
        ('full', 'Full Backup (Database + Media)'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    name = models.CharField(max_length=255)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, default='full')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True, help_text="Size in bytes")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'System Backup'
        verbose_name_plural = 'System Backups'
    
    def __str__(self):
        return f"{self.name} - {self.backup_type} ({self.status})"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    @property
    def file_exists(self):
        """Check if backup file exists"""
        if self.file_path and os.path.exists(self.file_path):
            return True
        return False
    
    def delete_file(self):
        """Delete the backup file from disk"""
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
                return True
            except OSError:
                return False
        return False