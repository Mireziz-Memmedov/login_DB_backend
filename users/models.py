from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class NewsUsers(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)

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

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.text[:20]}"