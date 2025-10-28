from django.urls import path
from . import views
#from .views import user_notifications

app_name = "Map"

urlpatterns = [
    path('', views.home, name="home"),
    path('maps/', views.map_list, name='map_list'),
    #path('maps/<int:map_id>/', views.map_detail, name='map_detail'),
    path('maps/create/', views.create_map, name='create_map'),
    path('edit/<int:map_id>/', views.edit_map, name='edit_map'),
    path('maps/<int:map_id>/', views.map_detail, name='map_detail'),  # For displaying the map
    #path('maps/upload/<int:map_id>/', views.upload_files, name='upload_files'),
    #path('notifications/', user_notifications, name='user_notifications'),


    # Add more URL patterns as needed
]
