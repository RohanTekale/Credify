from rest_framework import serializers
from .models import CreditCard, CardType
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class CardCreateSerializer(serializers.Serializer):
    card_type = serializers.CharField(max_length=50)
    income = serializers.DecimalField(max_digits=10, decimal_places=2)
    occupation = serializers.CharField(max_length=100)
    intended_use = serializers.CharField(max_length=200)
    is_single_use = serializers.BooleanField(default=False)


    def validate_card_type(self, value):
        try:
            card_type = CardType.objects.get(name=value)
        except CardType.DoesNotExist:
            raise serializers.ValidationError("Invalid card type")
        return card_type
    
    def validate_income(self, value):
        if value <= 0:
            raise serializers.ValidationError("Income must be greater than zero")
        return value
    
    def validate(self, data):
        user = self.context['request'].user
        if user.kyc_status != 'verified':
            raise serializers.ValidationError("KYC verification is required")
        if CreditCard.objects.filter(user=user, status__in=['active', 'frozen']).count() >= 3:
            raise serializers.ValidationError("Maximum 3 active or frozen cards allowed")
        if not user.is_active:
            raise serializers.ValidationError("User account is deactivated")
        return data

class CardStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCard
        fields = ['status']
        read_only_fields = ['status']

class CreditCardSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    card_type = serializers.CharField(source='card_type.name')  
    unmasked_card_number= serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)


    def get_card_number(self, obj):
        return f"**** **** **** {obj.card_number[-4:]}"
    
    def get_unmasked_card_number(self, obj):
        user = self.context['request'].user
        admin_view = self.context.get('admin_view',False)
        if (obj.is_single_use and obj.user == user) or admin_view or user.is_staff or getattr(user, 'is_support', False):
            return obj.card_number
        return None
    
    class Meta:
        model = CreditCard
        fields = ['id', 'card_type', 'card_number','unmasked_card_number', 'expiry_date', 'credit_limit','available_credit', 'status', 'nickname','is_single_use', 'created_at', 'updated_at', 'user_email']
        read_only_fields = ['id', 'card_type', 'card_number', 'unmasked_card_number','expiry_date', 'credit_limit', 'available_credit', 'status','created_at', 'updated_at', 'user_email']

    def to_representation(self, ret):
        ret = super().to_representation(ret)
        admin_view = self.context.get('admin_view', False)
        if not admin_view:
            ret.pop('user_email', None)
        return ret
        


