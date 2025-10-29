from django.contrib import admin
from django.urls import path
from . import views

app_name = "Login"

urlpatterns = [
    path('debug-db/', views.debug_database_connection, name='debug_database_connection'),
    #path('register/', views.register, name='register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/<str:username>/', views.edit_profile, name='edit_profile'),
    
    # Backup URLs
    path('backups/', views.backup_list, name='backup_list'),
    path('backups/create/', views.create_backup, name='create_backup'),
    path('backups/upload/', views.upload_backup, name='upload_backup'),
    path('backups/<int:backup_id>/restore/', views.restore_backup, name='restore_backup'),
    path('backups/<int:backup_id>/download/', views.download_backup, name='download_backup'),
    path('backups/<int:backup_id>/delete/', views.delete_backup, name='delete_backup'),
]