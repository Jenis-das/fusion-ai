from django.urls import path
from . import views
from .config import fusion_routes


urlpatterns = [
    path('', views.initialView, name=fusion_routes.chat_dashboard),
    path('/register', views.initialView, name=fusion_routes.register),
    path('/login', views.initialView, name=fusion_routes.login),
    path('/chats', views.initialView, name=fusion_routes.chat_dashboard),
]
