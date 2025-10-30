from django.urls import path
from . import views

app_name = 'task_mananger'

urlpatterns = [
    
   path('course/<int:course_id>/', views.course_program, name='course_program'),
    
]
