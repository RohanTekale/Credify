from rest_framework import serializers
from .models import CreditCard, CardType
from django.utils import timezone


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
        if CreditCard.objects.filter(user=user, status='active').count() >= 3:
            raise serializers.ValidationError("Maximum 3 active cards allowed")
        if not user.is_active:
            raise serializers.ValidationError("User account is deactivated")
        return data
    

class CreditCardSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    card_Type = serializers.CharField(source='card_type.name')  # ✅ updated field name
    unmasked_card_number= serializers.SerializerMethodField()


    def get_card_number(self, obj):
        return f"**** **** **** {obj.card_number[-4:]}"
    
    def get_unmasked_card_number(self, obj):
        user = self.context['request'].user
        if user.is_staff or getattr(user, 'is_support', False):
            return obj.card_number
        return None
    
    class Meta:
        model = CreditCard
        fields = ['id', 'card_Type', 'card_number','unmasked_card_number', 'expiry_date', 'credit_limit', 'available_credit', 'status', 'nickname']


