# downloader/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    
    path('', views.home_view, name='home'),
    path('cabinet/', views.cabinet_view, name='cabinet'),
    path('register/', views.register_view, name='register'),
    
    path('login/', auth_views.LoginView.as_view(template_name='downloader/login.html'), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
]