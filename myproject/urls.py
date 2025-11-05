
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage


# admin.site.site_title = "Welcome to our GIS Protal"
# admin.site.site_header = "GIS Portal Admin"
# admin.site.index_title = "GIS Full Control Pannel"

def toggle_sidebar(request):
    return HttpResponse('Sidebar toggled!')

urlpatterns = [
    #path('admin/', admin.site.urls),
    path('admin/', admin.site.urls),
    path('', include('Map.urls')),
    path('user/', include('Login.urls')),
    #path('auth/', include('django.contrib.auth.urls')),  # Temporarily disabled
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

