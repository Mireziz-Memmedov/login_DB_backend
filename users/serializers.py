from rest_framework import serializers
from .models import NewsUsers

class NewsUsersSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = NewsUsers
        fields = ['id', 'username', 'password']

