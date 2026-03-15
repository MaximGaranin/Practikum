from django.urls import path
from . import views

app_name = 'editor'

urlpatterns = [
    path('analyze/', views.analyze_code, name='analyze_code'),
    path('execute/', views.execute_code, name='execute_code'),
]

