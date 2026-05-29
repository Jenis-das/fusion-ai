from django.db import models
from django.contrib.auth.models import User


class Provider(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='providers')
    name = models.CharField(max_length=100)           # "OpenAI", "Anthropic"
    api_key = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class LLMModel(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)           
    model_id = models.CharField(max_length=100)       
    is_active = models.BooleanField(default=True)
    is_custom = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.provider.name} - {self.name}"


class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
    name = models.CharField(max_length=100)
    active_models = models.ManyToManyField(LLMModel, blank=True, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    llm_model = models.ForeignKey(LLMModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    is_judge_selected = models.BooleanField(default=False)  # Judge AI verdict
    time_stamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chat.name} - {self.role} - {self.time_stamp}"