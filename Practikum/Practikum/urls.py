from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from editor import views as editor_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('practikum.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('Logistic_Task.urls')),
    path('api/', include('editor.urls')),                              # /api/analyze/, /api/execute/
    path('editor/', editor_views.editor_view, name='editor'),         # /editor/
    path('editor/<int:task_id>/', editor_views.editor_view, name='editor_task'),  # /editor/5/
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

