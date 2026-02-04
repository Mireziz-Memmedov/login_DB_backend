from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class NewsUsers(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128, null=False)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=False)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True, default=timezone.now)
    verify_code = models.CharField(max_length=6, null=False, blank=True)
    verify_code_created_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    blocked_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = 'login'

    def __str__(self):
        return self.username

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

class Message(models.Model):
    sender = models.ForeignKey(NewsUsers, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(NewsUsers, related_name='received_messages', on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    deleted_for = models.JSONField(default=list)
    deleted_for_everyone = models.BooleanField(default=False)
    deleted_profile = models.JSONField(default=list)
    
    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.text[:20]}"