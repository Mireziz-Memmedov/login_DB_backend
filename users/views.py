from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NewsUsers, Message
from .serializers import NewsUsersSerializer, MessageSerializer
from django.db.models import Q, Max
from django.utils import timezone
from datetime import timedelta

# Signup
@api_view(['POST'])
def signup(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    
    if not username or not password or not email:
        return Response({'success': False, 'error': 'Bütün sahələr doldurulmalıdır!'})
    
    if NewsUsers.objects.filter(username=username).exists():
        return Response({'success': False, 'error': 'İstifadəçi adı artıq mövcuddur!'})
    
    if NewsUsers.objects.filter(email=email).exists():
        return Response({'success': False, 'error': 'Bu email ilə artıq hesab yaradılıb!'})
    
    user = NewsUsers(username=username, email=email)
    user.set_password(password)
    user.save()
    return Response({'success': True})

# Login
@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    try:
        user = NewsUsers.objects.get(username=username)
        if user.check_password(password):
            user.is_online = True
            user.last_seen = timezone.now()
            user.save(update_fields=["is_online", "last_seen"])
            return Response({'success': True, 'user': NewsUsersSerializer(user).data})
        else:
            return Response({'success': False, 'error': 'Şifrə yalnışdır!'})
    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı!'})

# Search user
@api_view(['POST'])
def search_user(request):
    query = request.data.get('username', '').strip()
    users = NewsUsers.objects.filter(username__iexact=query).values_list('username', flat=True)
    return Response({'users': list(users)})

# Recent chats
@api_view(['GET'])
def recent_chats(request):
    current_user_id = request.GET.get('user_id')
    if not current_user_id:
        return Response({'users': []})
    
    try:
        user = NewsUsers.objects.get(id=current_user_id)
        
        sent_to = Message.objects.filter(sender=user).values('receiver__username').annotate(last_time=Max('timestamp'))
        received_from = Message.objects.filter(receiver=user).values('sender__username').annotate(last_time=Max('timestamp'))
        
        chats = {}
        for item in sent_to:
            chats[item['receiver__username']] = item['last_time']
        for item in received_from:
            if item['sender__username'] in chats:
                chats[item['sender__username']] = max(chats[item['sender__username']], item['last_time'])
            else:
                chats[item['sender__username']] = item['last_time']

        sorted_users = sorted(chats.items(), key=lambda x: x[1], reverse=True)
        users_ordered = [username for username, _ in sorted_users]
        
        return Response({'users': users_ordered})
    except (NewsUsers.DoesNotExist, ValueError):
        return Response({'users': []})

# Send message
@api_view(['POST'])
def send_message(request):
    sender_id = request.data.get('sender_id')
    receiver_name = request.data.get('to')
    text = request.data.get('text')
    
    if not sender_id or not receiver_name or not text:
        return Response({'success': False, 'error': 'Bütün sahələr doldurulmalıdır!'})
    
    try:
        sender = NewsUsers.objects.get(id=sender_id)
        receiver = NewsUsers.objects.get(username=receiver_name)
        msg = Message(sender=sender, receiver=receiver, text=text)
        msg.save()
        return Response({'success': True})
    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı'})
    except ValueError:
        return Response({'success': False, 'error': 'ID səhv formatdadır'})

# Get messages
@api_view(['GET'])
def get_messages(request):
    current_user_id = request.GET.get('user_id')
    target_user_name = request.GET.get('user')
    
    if not current_user_id or not target_user_name:
        return Response({'messages': [], 'error': 'user_id və user tələb olunur'})
    
    try:
        user = NewsUsers.objects.get(id=current_user_id)
    except (NewsUsers.DoesNotExist, ValueError):
        return Response({'messages': [], 'error': 'İstifadəçi tapılmadı'})
    
    try:
        target_user = NewsUsers.objects.get(username=target_user_name)
    except NewsUsers.DoesNotExist:
        return Response({'messages': [], 'error': 'Hədəf istifadəçi tapılmadı'})

    unread_messages = Message.objects.filter(sender=target_user, receiver=user, is_read=False)
    unread_messages.update(is_read=True)

    msgs = Message.objects.filter(
        Q(sender=user, receiver=target_user) | Q(sender=target_user, receiver=user)
    ).order_by('timestamp')
    
    serializer = MessageSerializer(msgs, many=True)
    return Response({'messages': serializer.data})

# User status
@api_view(['GET'])
def user_status(request):
    username = request.GET.get('username')
    if not username:
        return Response({'error': 'username tələb olunur'}, status=400)

    try:
        user = NewsUsers.objects.get(username=username)
        
        if user.is_online and user.last_seen:
            now = timezone.now()
            if now - user.last_seen > timedelta(minutes=5):
                user.is_online = False
                user.save(update_fields=["is_online"])
        
        return Response({
            'username': user.username,
            'is_online': user.is_online,
            'last_seen': user.last_seen
        })
    except NewsUsers.DoesNotExist:
        return Response({'error': 'İstifadəçi tapılmadı'}, status=404)

# Logout
@api_view(['POST'])
def logout(request):
    user_id = request.data.get('user_id')
    try:
        user = NewsUsers.objects.get(id=user_id)
        user.is_online = False
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])
        return Response({'success': True})
    except NewsUsers.DoesNotExist:
        return Response({'success': False})
