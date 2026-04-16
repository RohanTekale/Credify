from rest_framework import serializers
from  .models import User,ReactivationRequest
from django.db import models
import cloudinary.uploader
from rest_framework_simplejwt.tokens import AccessToken

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_number', 'address']
    
    def validate(self, data):
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError('Email already exists')
        return data
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number', ''),
            address=validated_data.get('address', '')
        )
        return user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        username= data.get('username')
        email= data.get('email')
        password= data.get('password')

        if not (username or email):
            raise serializers.ValidationError('Username or Email is required')
        if not password:
            raise serializers.ValidationError('Password is required')
        
        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError('invalid Credentials')
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError('invalid Credentials')
        if not user.is_active:
            raise serializers.ValidationError('Account is deactivated. Please request reactivation.')
        
        if not user.check_password(password):
            raise serializers.ValidationError('invalid Credentials')
        
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'address', 'kyc_status', 'is_email_verified','is_staff','is_superuser', 'is_support']
        read_only_fields = ['kyc_status', 'is_email_verified']

class KYCUploadserializer(serializers.ModelSerializer):
    kyc_document = serializers.FileField(write_only=True)

    class Meta:
        model = User
        fields = ['kyc_document']
    
    def validate_kyc_document(self,value):
        if not value.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise serializers.ValidationError({"error": "Invalid file format. Only PDF, JPG, JPEG, or PNG allowed."})
        if value.size > 5 * 1024 * 1024: #5mb limit
            raise serializers.ValidationError({"error": "File size should not exceed 5MB limit"})
        return value
    
    def update(self, instance, validated_data):
        file = validated_data['kyc_document']
        upload_result = cloudinary.uploader.upload(file, folder='kyc_documents', resource_type ='auto')
        instance.kyc_document = upload_result['secure_url']
        instance.kyc_status = 'pending'
        instance.save()
        return instance
    
class KYCReviewSerializer(serializers.ModelSerializer):
    user_id  = serializers.IntegerField(write_only=True)
    kyc_status = serializers.ChoiceField(choices=['verified', 'rejected'])
    reviewer_comments = serializers.CharField(max_length=500,required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['user_id','kyc_status','reviewer_comments']
    def validate_user_id(self,value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "User not found"})
        return value
       
class PasswordChangeSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')

        if not (username or email):
            raise serializers.ValidationError({"error": "Username or email is required"})
        
        user = self.context['request'].user
        if username and username != user.username:
            raise serializers.ValidationError({"error": "Username does not match"})
        if email and email != user.email:
            raise serializers.ValidationError({"error": "Email does not match"})
        
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"error": "Old password is incorrect"})
        
        return data
    
class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(required =False, allow_blank=True)
    email = serializers.EmailField(required = False, allow_blank=True)

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')

        if not (username or email):
            raise serializers.ValidationError({"error": "Username or Email is required."})
        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError({"error": "User with this email does not exist."})
        else:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError({"error": "User with this username does not exist."})
        data['user'] = user
        return data
    
class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self,data):
        username = data.get('username')
        email = data.get('email')

        if not (username or email):
            raise serializers.ValidationError({"error": "Username or Email is required."})
        
        try:
            user = None
            if email:
                user = User.objects.get(email=email)
            else:
                user = User.objects.get(username=username)
            token = AccessToken(data['token'])
            if token['user_id'] != user.id:
                raise serializers.ValidationError({"error": "Invalid token"})
            data['user']=user
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "User with this username or email does not exist."})
        except Exception:
            raise serializers.ValidationError({"error": "Invalid token"})


class ReactivationRequestSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(required=True, write_only=True)
    reason = serializers.CharField(max_length= 500, required=True)
    class Meta:
        model = ReactivationRequest
        fields =['identifier','reason']

    def validate_identifier(self, value):
        try:
            user =User.objects.filter(
                models.Q(email=value) | models.Q(phone_number=value)
            ).first()
            if not user:
                raise serializers.ValidationError({"error": "User with this email or phone number does not exist,Please try again."})
            if user.is_active:
                raise serializers.ValidationError({"error": "User is already active"})
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "User with this email or phone number does not exist"})

    def create(self,validated_data):
        user = User.objects.filter(
            models.Q(email=validated_data['identifier']) |
            models.Q(phone_number=validated_data['identifier'])
        ).first()
        return ReactivationRequest.objects.create(user=user,reason=validated_data['reason'])
    
class ReactivationReviewSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(write_only=True)
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    admin_comments = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = ReactivationRequest
        fields = ['request_id', 'status', 'admin_comments']
    def validate_request_id(self, value):
        try:
            ReactivationRequest.objects.get(id=value, status='pending')
        except ReactivationRequest.DoesNotExist:
            raise serializers.ValidationError({"error": "Pending reactivation request not found"})
        return value