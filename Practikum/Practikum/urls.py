from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('practikum.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('auth/', include('registration.urls')),
]
