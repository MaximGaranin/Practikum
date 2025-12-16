from django.urls import path
from . import views

app_name = 'editor'

urlpatterns = [
    path('api/analyze/', views.analyze_code, name='analyze_code'),
    path('api/execute/', views.execute_code, name='execute_code'),
]
