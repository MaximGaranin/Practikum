from django.urls import path
from . import views

app_name = 'prac'

urlpatterns = [
    path('', views.course, name='course'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/<str:username>/edit/', views.edit_profile, name='edit_profile'),
    path('task/', views.task, name='task'),
    path('settings/', views.settings, name='settings'),
    path('auth/registration/', views.RegisterView.as_view(), name='registration'),
]
