from rest_framework import serializers
from .models import Transaction
from cards.models import CreditCard

class TransactionSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'card_id', 'amount', 'fee', 'status', 'description', 'created_at']
        read_only_fields = ['id', 'fee', 'status', 'created_at']

    def validate_card_id(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
        if not CreditCard.objects.filter(id=value, user=request.user, status='active').exists():
            raise serializers.ValidationError("Invalid or inactive card")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value