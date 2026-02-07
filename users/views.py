from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NewsUsers, Message
from .serializers import NewsUsersSerializer, MessageSerializer
from django.db.models import Q, Max
from django.utils import timezone
import math
from datetime import timedelta
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# Signup
@api_view(['POST'])
def signup(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')

    NewsUsers.objects.filter(
        is_active=False,
        verify_code_created_at__lt=timezone.now() - timedelta(minutes=5)
    ).delete()

    if not username or not password or not email:
        return Response({'success': False, 'error': 'Bütün sahələr doldurulmalıdır!'})

    try:
        validate_email(email)
    except ValidationError:
        return Response({'success': False, 'error': 'Email formatı düzgün deyil!'})

    if NewsUsers.objects.filter(username=username).exists():
        return Response({'success': False, 'error': 'İstifadəçi adı artıq mövcuddur!'})
    if NewsUsers.objects.filter(email=email).exists():
        return Response({'success': False, 'error': 'Bu email ilə artıq hesab yaradılıb!'})

    verify_code = generate_verify_code(6)

    user = NewsUsers.objects.create(
        username=username,
        email=email,
        is_active=False,
        verify_code=verify_code,
        verify_code_created_at=timezone.now()
    )
    user.set_password(password)
    user.save()

    send_mail(
        subject='Hesabın yaradılması üçün təsdiq kodu',
        message=f'Email təsdiqləmə kodu: {verify_code}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return Response({'success': True, 'message': 'Təsdiq kodu email-ə göndərildi'})

def generate_verify_code(length):
    characters = string.digits
    password = ''.join(random.choice(characters) for i in range(length))

    return password

# Login
@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    try:
        user = NewsUsers.objects.get(username=username)

        if not user.is_active:
            return Response({'success': False, 'error': 'Hesab təsdiqlənməyib!', 'user': NewsUsersSerializer(user).data})

        if user.blocked_until and user.blocked_until <= timezone.now():
            user.failed_attempts = 0
            user.blocked_until = None
            user.save(update_fields=["failed_attempts", "blocked_until"])

        if user.blocked_until and user.blocked_until > timezone.now():
            seconds_left = math.ceil(
                (user.blocked_until - timezone.now()).total_seconds()
            )
            return Response({'success': False, 'seconds_left': seconds_left, 'error': f'{seconds_left} saniyə sonra yenidən cəhd edin'})

        if not user.check_password(password):
            user.failed_attempts += 1
            if user.failed_attempts >= 3:
                user.blocked_until = timezone.now() + timedelta(seconds=30)
            user.save(update_fields=["failed_attempts", "blocked_until"])

            error_msg = f'{user.blocked_until.isoformat()}, sonra yenidən cəhd edin' if user.failed_attempts >= 3 else "Şifrə yanlışdır"
            return Response({'success': False, 'error': error_msg, 'user': NewsUsersSerializer(user).data})
        else:
            user.failed_attempts = 0
            user.blocked_until = None
            user.is_online = True
            user.last_seen = timezone.now()
            user.save(update_fields=["failed_attempts", "blocked_until", "is_online", "last_seen"])

            return Response({'success': True, 'user': NewsUsersSerializer(user).data})

    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı!'})

# Search user
@api_view(['POST'])
def search_user(request):
    query = request.data.get('username', '').strip()
    users = NewsUsers.objects.filter(username__exact=query).values_list('username', flat=True)
    return Response({'users': list(users)})

# Recent chats
@api_view(['GET'])
def recent_chats(request):
    current_user_id = request.GET.get('user_id')
    if not current_user_id:
        return Response({'users': []})
    
    try:
        user = NewsUsers.objects.get(id=current_user_id)

        sent_to = Message.objects.filter(sender=user).exclude(deleted_profile__contains=[user.id]).values('receiver__username').annotate(last_time=Max('timestamp'))
        received_from = Message.objects.filter(receiver=user).exclude(deleted_profile__contains=[user.id]).values('sender__username').annotate(last_time=Max('timestamp'))
        
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
    limit = int(request.GET.get('limit', 10))
    offset = int(request.GET.get('offset', 0))
    limit = min(limit, 50) 

    if not current_user_id or not target_user_name:
        return Response({'messages': [], 'error': 'user_id və user tələb olunur'})

    try:
        user = NewsUsers.objects.get(id=current_user_id)
        target_user = NewsUsers.objects.get(username=target_user_name)
    except NewsUsers.DoesNotExist:
        return Response({'messages': [], 'error': 'İstifadəçi tapılmadı'})

    current_user_id = int(current_user_id)

    Message.objects.filter(sender=target_user, receiver=user, is_read=False).update(is_read=True)

    visible_msgs = Message.objects.filter(
        Q(sender=user, receiver=target_user) | Q(sender=target_user, receiver=user),
        deleted_for_everyone=False
    ).exclude(deleted_for__contains=[current_user_id]).exclude(deleted_profile__contains=[current_user_id])

    total_visible = visible_msgs.count()

    msgs = visible_msgs.order_by('-timestamp')[offset:offset + limit]

    serializer = MessageSerializer(msgs, many=True)

    return Response({
        'messages': serializer.data[::-1],
        'has_more': total_visible > offset + limit
    })

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

#Forgot check
@api_view(['POST'])
def forgot_check(request):

    username_or_email = request.data.get('username_or_email')
    user = NewsUsers.objects.filter(Q(username=username_or_email) | Q(email=username_or_email))

    if user.exists():
        verify_code = generate_verify_code(6)
        user_instance = user.first()
        user_instance.verify_code = verify_code
        user_instance.verify_code_created_at = timezone.now()
        user_instance.save()

        send_mail(
            subject='Şifrə bərpası üçün təsdiq kodu',
            message=f'Sizin şifrə bərpa kodunuz: {verify_code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_instance.email],
            fail_silently=False,
        )

        return Response({'success': True})
    else:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı'})

#Verify Code
@api_view(['POST'])
def verify_code(request):
    verify_code = request.data.get('verify_code')
    dual = request.data.get('dual')

    user_instance = NewsUsers.objects.filter(verify_code=verify_code).first()

    if not user_instance:
        return Response({'success': False, 'error': 'Kod yanlışdır'})

    if timezone.now() - user_instance.verify_code_created_at > timedelta(minutes=5):
        return Response({'success': False, 'error': 'Kodun vaxtı bitib'})

    if dual == 'signup':
        user_instance.is_active = True
        user_instance.verify_code = ''
        user_instance.verify_code_created_at = None
        user_instance.save()
    elif dual == 'forgot':
        pass

    return Response({
        'success': True,
        'dual': dual,
        'user_id': user_instance.id,
        'username': user_instance.username
    })

#Reset password
@api_view(['POST'])
def reset_password(request):
    password = request.data.get('password')
    verify_code = request.data.get('verify_code')

    if not password:
        return Response({'success': False, 'error': 'Yeni şifrə daxil edin!'})
    if not verify_code:
        return Response({'success': False, 'error': 'Kod göndərilməyib!'})

    try:
        user = NewsUsers.objects.get(verify_code=verify_code)
    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'Kod yanlışdır və ya vaxtı bitib'})
    
    if not user.verify_code_created_at:
        return Response({'success': False, 'error': 'Kodun yaradılma vaxtı yoxdur, yenidən kod göndərin!'})

    if user.verify_code_created_at and timezone.now() - user.verify_code_created_at > timedelta(minutes=5):
        return Response({'success': False, 'error': 'Kodun vaxtı bitib'})

    user.set_password(password)
    user.verify_code = ''
    user.verify_code_created_at = None
    user.save()

    return Response({'success': True})

# Delete message
@api_view(['POST'])
def delete_chat(request):
    try:
        current_user_id = int(request.data.get('user_id'))
        message_id = int(request.data.get('msg_id'))
    except (TypeError, ValueError):
        return Response({'success': False, 'error': 'ID-lər düzgün deyil'})

    try:
        msg = Message.objects.get(id=message_id)
    except Message.DoesNotExist:
        return Response({'success': False, 'error': 'Mesaj tapılmadı'})

    if current_user_id == msg.sender.id or current_user_id == msg.receiver.id:
        if current_user_id not in msg.deleted_for:
            msg.deleted_for.append(current_user_id)
            msg.save()
        return Response({'success': True})
    else:
        return Response({'success': False, 'error': 'Mesajı silmək icazən yoxdur'})

# Unsend message
@api_view(['POST'])
def unsend_chat(request):
    try:
        current_user_id = int(request.data.get('user_id')) 
        message_id = int(request.data.get('msg_id'))
    except (TypeError, ValueError):
        return Response({'success': False, 'error': 'ID-lər düzgün deyil'})

    try:
        msg = Message.objects.get(id = message_id)
    except Message.DoesNotExist:
        return Response({'success': False, 'error': 'Mesaj tapılmadı'})

    if current_user_id == msg.sender.id:
        msg.deleted_for_everyone = True
        msg.save()
        return Response({'success': True})
    else:
        return Response({'success': False, 'error': 'Mesajı silmək icazən yoxdur'})

#Delete profil chat
@api_view(['POST'])
def delete_profile_chats(request):
    try:
        current_user_id = int(request.data.get('user_id'))
        target_username = request.data.get('target_username')
    except (TypeError, ValueError):
        return Response({'success': False, 'error': 'ID düzgün deyil'}) 

    try:
        user = NewsUsers.objects.get(id=current_user_id)
        target_user = NewsUsers.objects.get(username=target_username)

        user_messages = Message.objects.filter(
            Q(sender=user, receiver=target_user) |
            Q(sender=target_user, receiver=user)
        )

        for msg in user_messages:
            if current_user_id not in msg.deleted_profile:
                msg.deleted_profile.append(current_user_id)
                msg.save(update_fields=['deleted_profile'])

        return Response({'success': True})

    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı'})

Delete Profile Forever
@api_view(['POST'])
def deleted_profile_forever(request):
    username = request.data.get('currentUsername')
    password = request.data.get('password')

    if not username or not password:
        return Response({'success': False, 'error': 'Username və password mütləqdir!'})

    try:
        user = NewsUsers.objects.get(username=username)
    except NewsUsers.DoesNotExist:
        return Response({'success': False, 'error': 'İstifadəçi tapılmadı!'})

    if not user.check_password(password):
        return Response({'success': False, 'error': 'Password yanlışdır!'})
    
    user.delete()
    return Response({'success': True, 'message': 'Profil uğurla silindi!'})

    

