from rest_framework.response import Response
from rest_framework.views import APIView
from .models import NewsUsers
from .serializers import NewsUsersSerializer

class SignupAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if len(password) < 6:
            return Response({"success": False, "error": "Şifrə minimum 6 simvol olmalıdır!"})

        if not username or not password:
            return Response({'success': False, 'error': 'Bütün sahələr doldurulmalıdır!'})

        if NewsUsers.objects.filter(username=username).exists():
            return Response({'success': False, 'error': 'Bu istifadəçi adı artıq mövcuddur!'})

        user = NewsUsers(username=username)
        user.set_password(password)
        user.save()

        return Response({'success': True})

class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = NewsUsers.objects.get(username=username)
        except NewsUsers.DoesNotExist:
            return Response({'success': False, 'error': 'İstifadəçi adı və ya şifrə yanlışdır!'})

        if not user.check_password(password):
            return Response({'success': False, 'error': 'İstifadəçi adı və ya şifrə yanlışdır!'})

        return Response({'success': True})
        