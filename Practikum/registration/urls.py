from django.urls import path
from . import views

app_name = 'reg'

urlpatterns = [
    path('registration/', views.RegisterView.as_view(), name='registration'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/<str:username>/edit/', views.edit_profile, name='edit_profile'),
]
