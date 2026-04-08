from rest_framework import serializers
from .models import CreditCard, CardType,Subscription
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
        card_type = data['card_type']
        if user.kyc_status != 'verified':
            raise serializers.ValidationError("KYC verification is required")
        if CreditCard.objects.filter(user=user, status__in=['active', 'frozen']).count() >= 3:
            raise serializers.ValidationError("Maximum 3 active or frozen cards allowed")
        if not user.is_active:
            raise serializers.ValidationError("User account is deactivated")
        if card_type.min_income_for_permanent > user.income:
            raise serializers.ValidationError(f"Income too low for permanent {card_type.name} card ")
        return data

class CardStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCard
        fields = ['id','status']
        read_only_fields = ['status']

class CreditCardSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    base_card_type = serializers.CharField(source= 'base_card_type.name')
    effective_card_type = serializers.CharField(source='effective_card_type.name')
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
        fields = ['id', 'base_card_type', 'effective_card_type', 'card_number','unmasked_card_number', 'expiry_date', 'credit_limit','original_credit_limit','available_credit', 'status', 'nickname','is_single_use', 'created_at', 'updated_at', 'user_email']
        read_only_fields = ['id', 'base_card_type', 'effective_card_type', 'card_number', 'unmasked_card_number','expiry_date', 'credit_limit', 'original_credit_limit','available_credit', 'status','created_at', 'updated_at', 'user_email']

    def to_representation(self, ret):
        ret = super().to_representation(ret)
        admin_view = self.context.get('admin_view', False)
        if not admin_view:
            ret.pop('user_email', None)
        return ret
    
class SubscriptionCreateSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    card_type = serializers.CharField(max_length=50)
    is_limited_time = serializers.BooleanField(default=False)

    def validate_card_id(self, value):
        try:
            card = CreditCard.objects.get(id=value)
        except CreditCard.DoesNotExist:
            raise serializers.ValidationError("Card not found")
        if card.user != self.context['request'].user:
            raise serializers.ValidationError("You can only subscribe to your own card")
        return value
    
    def validate_card_type(self, value):
        try:
            card_type = CardType.objects.get(name=value)
        except CardType.DoesNotExist:
            raise serializers.ValidationError("Invalid card type")
        return card_type
    
    def validate(self, data):
        card = CreditCard.objects.get(id=data['card_id'])
        card_type = data['card_type']
        if  card.base_card_type ==card_type:
            raise serializers.ValidationError("Subscription card type must differ from base card type")
        if card.status!='active':
            raise serializers.ValidationError("Card must be active to subscribe")
        if Subscription.objects.filter(card=card,status='active').exists():
            raise serializers.ValidationError("Card already has an active subscription")
        return data
        
class SubscriptionSerializer(serializers.ModelSerializer):
    card_type = serializers.CharField(source='card_type.name')
    user_email = serializers.EmailField(source = 'user.email', read_only=True)
    card_base_type = serializers.CharField(source='card.base_card_type.name', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'user_email', 'card', 'card_base_type','card_type', 'status', 'is_limited_time', 
                 'subscription_start', 'subscription_end', 'subscription_fee', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_email', 'card', 'card_base_type','status', 'subscription_start', 
                           'subscription_end', 'subscription_fee', 'created_at', 'updated_at']

class SubscriptionUpgradeSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField()
    new_card_type = serializers.CharField(max_length=50)
    is_limited_time = serializers.BooleanField(default=False)


    def validate_card_id(self, value):
        try:
            card = CreditCard.objects.get(id=value)
        except CreditCard.DoesNotExist:
            raise serializers.ValidationError("card not found")
        if card.user != self.context['request'].user:
            raise serializers.ValidationError("You can only upgrade your own card")
        return value
    
    def validate_new_card_type(self,value):
        try:
            card_type =  CardType.objects.get(name=value)
        except CardType.DoesNotExist:
            raise serializers.ValidationError("invalid card type")
        return card_type
    
    def validate(self, data):
        card = CreditCard.objects.get(id=data['card_id'])
        new_card_type= data['new_card_type']

        if card.card_type == new_card_type:
            raise serializers.ValidationError("New card type must be different from current card type")
        if new_card_type.requires_admin_approval:
            raise serializers.ValidationError("Upgrading to this card type requires admin approval")
        return data
        
        

        