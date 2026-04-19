from rest_framework import serializers
from .models import UserRequest


class RaiseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = ['request_type','description']

    def validate(self,data):
        if data['request_type']== 'other' and not data.get('description'):
            raise serializers.ValidationError({"description":"Please describe your request when selecting 'Other'."})
        return data
    
    def create(self, validated_data):
        return UserRequest.objects.create(user=self.context['request'].user, **validated_data)

class  UserRequestListSerializer(serializers.ModelSerializer):
    request_id = serializers.SerializerMethodField()

    class Meta:
        model = UserRequest
        fields= ['request_id', 'request_type', 'description','status', 'admin_comment', 'user_comment', 'document', 'created_at', 'updated_at',]

    def get_request_id(self,obj):
        return f"REQ-{obj.id}"

class AdminRequestListSerializer(serializers.ModelSerializer):
    request_id =serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.username',read_only=True)
    user_email = serializers.EmailField(source='user.email',read_only=True)

    class Meta:
        model = UserRequest
        fields = ['request_id', 'user_id', 'user_name', 'user_email','request_type', 'description', 'status','admin_comment', 'user_comment', 'document','created_at', 'updated_at',]

    def get_request_id(self,obj):
        return f"REQ-{obj.id}"
    
class AdminActionSerializer(serializers.Serializer):
    status  = serializers.ChoiceField(choices=['in_process', 'completed', 'rejected'])
    admin_comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)

class UserCommentSerializer(serializers.Serializer):
    user_comment = serializers.CharField(max_length=1000)

class DocumentUploadSerializer(serializers.Serializer):
    document = serializers.FileField()

    def validate(self,value):
        if not value.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise serializers.ValidationError("Unsupported file type. Only PDF, JPG, JPEG, PNG allowed.")
        if not value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds the limit of 5MB.")
        return value