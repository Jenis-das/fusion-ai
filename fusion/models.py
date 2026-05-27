from django.db import models
from django.contrib.auth.models import User


class LLMS(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(300)


class CHATS(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class MESSAGE(models.Model):
    chats = models.ForeignKey(CHATS, on_delete=models.CASCADE)
    llms = models.ForeignKey(LLMS, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    content = models.TextField()
    time_stamp = models.DateTimeField(auto_now_add=True)



