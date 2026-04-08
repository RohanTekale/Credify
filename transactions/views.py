from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction 
from .models import Transaction
from cards.models import CreditCard
from .serializers import TransactionSerializer
from decimal import Decimal
import logging
from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [FormParser, JSONParser, MultiPartParser]

    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'is_support', False):
            return Transaction.objects.all()
        return Transaction.objects.filter(card__user=self.request.user)
    
    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={201: "Transaction created successfully", 400: "Invalid request"})
    def create_transaction(self, request):
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():

                card_id = serializer.validated_data['card_id']
                amount = Decimal(str(serializer.validated_data['amount']))  # Convert to Decimal
                description = serializer.validated_data.get('description', '')

                card = (CreditCard.objects.select_for_update().select_related("card_type").get(id=card_id,user=request.user))
                if card.status != 'active':
                    logger.warning(f"Card {card_id} is not active for user {request.user.id}")
                    return Response({"error": "Card is not active"}, status=status.HTTP_400_BAD_REQUEST)
                
                fee = amount * Decimal(str(card.card_type.transaction_fee)) / Decimal('100')
                total_amount = amount + fee

                if total_amount > card.available_credit:
                    logger.warning(f"Insufficient credit for card {card_id}: {total_amount} > {card.available_credit}")
                    return Response({"error": "Insufficient available credit"}, status=status.HTTP_400_BAD_REQUEST)
                
                transaction = Transaction.objects.create(
                    card=card,
                    amount=amount,
                    fee=fee,
                    status='success' if not card.is_single_use else 'pending',
                    description=description
                )

                card.available_credit -= total_amount
                if card.is_single_use:
                    card.status = 'blocked'
                card.save(update_fields=['available_credit', 'status'])

                logger.info(f"Transaction {transaction.id} created for card {card_id} by user {request.user.id}")
                return Response(
                    TransactionSerializer(transaction).data,
                    status=status.HTTP_201_CREATED
                )
        except CreditCard.DoesNotExist:
            logger.error(f"Card {card_id} not found for user {request.user.id}")
            return Response({"error": "Card not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Transaction creation failed: {str(e)}", exc_info=True)
            capture_exception(e)
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)