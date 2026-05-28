from django.urls import path
from . import views
from .views import fusion
from .config import fusion_routes

# Routes Objects
fusions = fusion()

urlpatterns = [
    path('', views.initialView, name=fusion_routes.chats_dashboard),
    path('register/', fusions.register, name=fusion_routes.register),
    path('login/', fusions.login, name=fusion_routes.login),
    path('logout/', fusions.logout, name=fusion_routes.logout),
    path('dashboard/', fusions.chat_dashboard, name=fusion_routes.chats_dashboard),
    # path('history/', fusions.chatHistory, name=fusion_routes.chat_dashboard),
    # path('chats/<int:id>/', fusions.current_chat, name=fusion_routes.chat_dashboard),
]
