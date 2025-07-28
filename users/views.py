from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt
from .models import User,KYCReviewLog,ReactivationRequest
from .serializers import (
    UserRegistrationSerializer,LoginSerializer,UserProfileSerializer, KYCUploadserializer, KYCReviewSerializer, PasswordChangeSerializer,ForgotPasswordSerializer,ResetPasswordSerializer,ReactivationRequestSerializer,ReactivationReviewSerializer)
from .permissions import IsSupportStaff
from .tasks import send_kyc_notification_email, send_reactivation_notification_email

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.FormParser, parsers.JSONParser, parsers.MultiPartParser]

    def get_permissions(self):
        if self.action in ['register', 'login','forgot_password', 'reset_password','request_reactivation']:
            return [AllowAny()]
        elif self.action in [ 'kyc_review','review_reactivation']:
            return [IsSupportStaff()]
        return [IsAuthenticated()]

    def get_queryset(self):
        # Restrict Standard Users to their own data; Admins/Support see all
        if self.request.user.is_staff or self.request.user.is_support:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id, is_active=True)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not (request.user.is_staff or request.user.is_support):
            return Response({"error": "Only staff or support can deactivate users"}, status=status.HTTP_403_FORBIDDEN)
        instance.is_active = False
        instance.save()
        return Response({"message": "User deactivated successfully"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={201: "User registered successfully"})
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "User registered successfully",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={200: "JWT Token Pair"})
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'put'])
    @swagger_auto_schema(responses={200: UserProfileSerializer}, request_body=UserProfileSerializer)
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Profile updated successfully"})
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(responses={200: "KYC document uploaded successfully"})
    def kyc_upload(self, request):
        serializer = KYCUploadserializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "KYC document uploaded successfully"}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(responses={200: "KYC document reviewed successfully"})
    def kyc_review(self, request, pk=None):
        serializer = KYCReviewSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(id=serializer.validated_data['user_id'])
            user.kyc_status = serializer.validated_data['kyc_status']
            user.save()
            KYCReviewLog.objects.create(
                user=user,
                reviewer=request.user,
                kyc_status=serializer.validated_data['kyc_status'],
                comments= serializer.validated_data.get('reviewer_comments', '')
            )
            # send_kyc_notification_email.delay(
            #     user.email,
            #     serializer.validated_data['kyc_status'],
            #     serializer.validated_data.get('reviewer_comments', '')

            # )
            return Response({"message": f"KYC status updated to {serializer.validated_data['kyc_status']}"}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST) 

    @action(detail=False, methods=['post'])
    @swagger_auto_schema(responses={200: "Password changed successfully"})
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False,methods=['post'])
    @swagger_auto_schema(responses={200:"Password reset token generated"})
    def  forgot_password(self,request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = RefreshToken.for_user(user).access_token
            return Response({"message": "Password reset token generated", "token": str(token)},status=status.HTTP_200_OK)
        return Response({"error":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False,methods=['post'])
    @swagger_auto_schema(responses={200:"Password reset successful"})
    def reset_password(self,request):
        serializer = ResetPasswordSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password reset successfully"},status=status.HTTP_200_OK)
        return Response({"error":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False,methods=['post'])
    @swagger_auto_schema(responses={201: "Reactivation request submitted successfully"})
    def request_reactivation(self, request):
        serializer = ReactivationRequestSerializer(data=request.data,context={'request': request})
        if serializer.is_valid():
            reactivation_request = serializer.save()
            return Response({"message": "Reactivation request submitted successfully","request_id": reactivation_request.id,"status": reactivation_request.status}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['post'])
    @swagger_auto_schema(responses={200: "Reactivation request reviewed successfully"})
    def review_reactivation_request(self, request):
        serializer = ReactivationReviewSerializer(data=request.data)
        if serializer.is_valid():
            reactivation_request = ReactivationRequest.objects.get(id=serializer.validated_data['request_id'])
            reactivation_request.status = serializer.validated_data['status']
            reactivation_request.admin_comments = serializer.validated_data.get('admin_comments', '')
            reactivation_request.save()
            if reactivation_request.status == 'approved':
                reactivation_request.user.is_active = True
                reactivation_request.user.save()
            # send_reactivation_notification_email.delay(
            #     reactivation_request.user.email, 
            #     reactivation_request.status,
            #     serializer.validated_data.get('admin_comments', '')
            # )
            return Response({"message": f"Reactivation request {reactivation_request.status}"}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class CustomTokenObtainPairView(TokenObtainPairView):
    pass