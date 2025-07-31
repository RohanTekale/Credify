from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt
from .models import CreditCard, CardType, CardRequest
from .serializers import CardCreateSerializer, CreditCardSerializer
from users.permissions import IsSupportStaff
from django.contrib.auth import get_user_model
from .utils import generate_card_number, generate_cvv, calculate_expiry_date
from django.contrib.auth.hashers import make_password
from notifications.tasks import notify_admin_card_approve

User = get_user_model()


class CardViewSet(viewsets.ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [FormParser, JSONParser, MultiPartParser]

    def get_permissions(self):
        if self.action in ['create_card']:
            return [IsAuthenticated()]
        elif self.action in ['approve_card_request']:
            return [IsSupportStaff()]
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_support:
            return CreditCard.objects.all()
        return CreditCard.objects.filter(user=self.request.user, status__in=['active', 'frozen'])

    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={201: "Card created successfully", 202: "Card request queued for approval"})
    def create_card(self, request):
        serializer = CardCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            card_type = serializer.validated_data['card_type']
            is_single_use = serializer.validated_data['is_single_use']

            if card_type.requires_admin_approval:
                card_request = CardRequest.objects.create(
                    user=user,
                    card_type=card_type,
                    is_single_use=is_single_use,
                    income=serializer.validated_data['income'],
                    occupation=serializer.validated_data['occupation'],
                    intended_use=serializer.validated_data['intended_use']
                )
                # notify_admin_card_approve.delay(card_request.id, user.id)
                return Response(
                    {"message": "Card request queued for admin approval", "request_id": card_request.id},
                    status=status.HTTP_202_ACCEPTED
                )

            try:
                card_number, hashed_number = generate_card_number()
                card = CreditCard.objects.create(
                    user=user,
                    card_type=card_type,
                    card_number=hashed_number,
                    cvv=make_password(generate_cvv()),
                    expiry_date=calculate_expiry_date(card_type),
                    credit_limit=card_type.default_credit_limit,
                    available_credit=card_type.default_credit_limit,
                    is_single_use=is_single_use
                )
                return Response(
                    CreditCardSerializer(card).data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                from sentry_sdk import capture_exception
                capture_exception(e)
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={201: "Card created successfully", 200: "Card request rejected"})
    def approve_card_request(self, request):
        request_id = request.data.get('request_id')
        approve = request.data.get('approve', True)

        try:
            card_request = CardRequest.objects.get(id=request_id)
            if not approve:
                card_request.status = 'rejected'
                card_request.save()
                return Response({"message": "Card request rejected"}, status=status.HTTP_200_OK)

            card_number, hashed_number = generate_card_number()
            card = CreditCard.objects.create(
                user=card_request.user,
                card_type=card_request.card_type,
                card_number=hashed_number,
                cvv=make_password(generate_cvv()),
                expiry_date=calculate_expiry_date(card_request.card_type),
                credit_limit=card_request.card_type.default_credit_limit,
                available_credit=card_request.card_type.default_credit_limit,
                is_single_use=card_request.is_single_use
            )
            card_request.status = 'approved'
            card_request.save()
            return Response(
                CreditCardSerializer(card).data,
                status=status.HTTP_201_CREATED
            )
        except CardRequest.DoesNotExist:
            return Response({"error": "Card request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            from sentry_sdk import capture_exception
            capture_exception(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
