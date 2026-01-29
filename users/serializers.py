from rest_framework import serializers
from .models import NewsUsers, Message

class NewsUsersSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = NewsUsers
        fields = ['id', 'username', 'password', 'email', 'is_online', 'last_seen', 'failed_attempts', 'blocked_until', 'is_active']

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source='sender.username', read_only=True)
    receiver = serializers.CharField(source='receiver.username')

    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'text', 'timestamp', 'is_read']