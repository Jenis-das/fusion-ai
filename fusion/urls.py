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
    path('setting/', fusions.settings, name=fusion_routes.setting),
    path('chat-dashboard/', fusions.chat_dashboard, name=fusion_routes.chats_dashboard),
    path('api-keys/', fusions.apikeys, name=fusion_routes.apikeys),
    path('history/', fusions.history, name=fusion_routes.history),
    path('new_chat/', fusions.new_chat, name=fusion_routes.new_chat),
    path('delete-chat/<int:id>', fusions.delete_chat, name="delete-chat"),
    path('chat-dashboard/<int:id>', fusions.current_chat, name='current_chat'),
    path('chat-dashboard/<int:id>/send', fusions.send_message, name='send_message'),
]