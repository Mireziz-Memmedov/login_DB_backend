from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NewsUsers, Message
from .serializers import NewsUsersSerializer, MessageSerializer
from django.db.models import Q

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
            return Response({'success': True, 'user': NewsUsersSerializer(user).data})
        else:
            return Response({'success': False, 'error': 'Şifrə yalnışdır!'})
    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı!'})

# User search
@api_view(['POST'])
def search_user(request):
    query = request.data.get('username', '')
    users = NewsUsers.objects.filter(username__icontains=query).values_list('username', flat=True)
    return Response({'users': list(users)})

# Recent chats
@api_view(['GET'])
def recent_chats(request):
    current_user_id = request.GET.get('user_id')
    if not current_user_id:
        return Response({'users': []})
    try:
        user = NewsUsers.objects.get(id=current_user_id)
        sent_to = Message.objects.filter(sender=user).values_list('receiver__username', flat=True)
        received_from = Message.objects.filter(receiver=user).values_list('sender__username', flat=True)
        users = set(list(sent_to) + list(received_from))
        return Response({'users': list(users)})
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

    msgs = Message.objects.filter(
        Q(sender=user, receiver=target_user) | Q(sender=target_user, receiver=user)
    ).order_by('timestamp')

    serializer = MessageSerializer(msgs, many=True)
    return Response({'messages': serializer.data})