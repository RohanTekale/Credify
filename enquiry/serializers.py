from rest_framework import serializers
from .models import UserRequest,EnquiryComment,EnquiryStatusLog,REQUEST_TYPES,SLA_HOURS
import cloudinary.uploader





class  EnquiryCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username',read_only=True)

    class Meta:
        model = EnquiryComment
        fields = ['id','author_name','body','is_internal','created_at']

class PublicCommentsSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username',read_only=True)
    class Meta:
        model = EnquiryComment
        fields = ['id','author_name','body','created_at']

class EnquiryStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username',read_only=True)

    class Meta:
        model = EnquiryStatusLog
        fields = ['id','changed_by_name','old_status','new_status','comment','changed_at']

class RaiseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = ['request_type','description','priority']

    def validate(self,data):
        if data['request_type']== 'other' and not data.get('description', '').strip():
            raise serializers.ValidationError({"description":"Please describe your request when selecting 'Other'."})
        return data
    
    def create(self, validated_data):
        instance = UserRequest(**validated_data,user=self.context['request'].user)
        instance.save()
        return instance

class  UserRequestListSerializer(serializers.ModelSerializer):
    request_id = serializers.SerializerMethodField()
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    sla_hours = serializers.SerializerMethodField()
    reraise_count = serializers.SerializerMethodField()
    can_rate = serializers.SerializerMethodField()
    class Meta:
        model = UserRequest
        fields = [
            'request_id',
            'request_type', 'request_type_display',
            'description',
            'status', 'status_display',
            'priority', 'priority_display',
            'sla_deadline', 'sla_breached',
            'sla_hours',
            'document',
            'user_rating', 'user_feedback',
            'is_viewed_by_user',
            'resolved_at',
            'reraise_count',
            'can_rate',
            'created_at', 'updated_at',
        ]

    def get_request_id(self,obj):
        return f"REQ-{obj.id}"

    def get_sla_hours(self,obj):
        return SLA_HOURS.get(obj.priority,48)
    
    def get_reraise_count(self,obj):
        return obj.reraises.count()
    
    def get_can_rate(self,obj):
        return obj.status == 'completed' and obj.user_rating is None

class UserRequestDetailSerializer(UserRequestListSerializer):
    comments = serializers.SerializerMethodField()
    history = EnquiryStatusLogSerializer(many=True, read_only=True)

    class Meta(UserRequestListSerializer.Meta):
        fields = UserRequestListSerializer.Meta.fields + ['comments','history']
    
    def get_comments(self,obj):
        public_comments = obj.comments.filter(is_internal=False)
        return PublicCommentsSerializer(public_comments, many=True).data

class AdminRequestListSerializer(serializers.ModelSerializer):
    request_id =serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.username',read_only=True)
    user_email = serializers.EmailField(source='user.email',read_only=True)
    assigned_to_name = serializers.CharField(source = 'assigned_to.username', read_only=True,default=None)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display= serializers.CharField(source='get_priority_display', read_only=True)
    reraise_count  = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = UserRequest
        fields = [
            'request_id',
            'user_id', 'user_name', 'user_email',
            'request_type', 'request_type_display',
            'description',
            'status', 'status_display',
            'priority', 'priority_display',
            'assigned_to', 'assigned_to_name',
            'sla_deadline', 'sla_breached',
            'document',
            'user_rating', 'user_feedback',
            'resolved_at',
            'reraise_count',
            'comment_count',
            'created_at', 'updated_at',
        ]


    def get_request_id(self,obj):
        return f"REQ-{obj.id}"
    
    def get_reraise_count(self,obj):
        return obj.reraises.count()
    
    def get_comment_count(self,obj):
        return obj.comments.count()
    
class AdminRequestDetailSerializer(AdminRequestListSerializer):
    comments = EnquiryCommentSerializer(many=True, read_only=True)
    history = EnquiryStatusLogSerializer(many=True, read_only=True)

    class Meta(AdminRequestListSerializer.Meta):
        fields = AdminRequestListSerializer.Meta.fields + ['comments','history']

    
class AdminActionSerializer(serializers.Serializer):
    status  = serializers.ChoiceField(choices=['in_process', 'completed', 'rejected'])
    admin_comment = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    is_internal = serializers.BooleanField(default=False)

class AssignRequestSerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField(help_text="User ID of the support agent to assign to")

class AdminCommentSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)
    is_internal = serializers.BooleanField(default=False)
class UserCommentSerializer(serializers.Serializer):
    user_comment = serializers.CharField(max_length=2000)

class DocumentUploadSerializer(serializers.Serializer):
    document = serializers.FileField()

    def validate(self,value):
        if not value.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise serializers.ValidationError("Unsupported file type. Only PDF, JPG, JPEG, PNG allowed.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds the limit of 5MB.")
        return value

class RatingSerializer(serializers.Serializer):
    user_rating = serializers.IntegerField(min_value=1, max_value=5)
    user_feedback = serializers.CharField(max_length=2000, required=False, allow_blank=True)