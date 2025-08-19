from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt
from .models import CreditCard, CardType, CardRequest
from .serializers import CardCreateSerializer, CreditCardSerializer, CardStatusSerializer
from .permissions import IsSupportOrCardOwner
from users.permissions import IsSupportStaff
from django.contrib.auth import get_user_model
from .utils import generate_card_number, generate_cvv, calculate_expiry_date,calculate_credit_limit
from django.contrib.auth.hashers import make_password
from notifications.tasks import notify_admin_card_approve,send_card_status_notification
from django.utils import timezone

User = get_user_model()


class CardViewSet(viewsets.ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [FormParser, JSONParser, MultiPartParser]

    def get_permissions(self):
        if self.action in ['create_card']:
            return [IsAuthenticated()]
        elif self.action in ['approve_card_request', 'freeze', 'unfreeze', 'unblock','list_admin_cards']:
            return [IsSupportStaff()]
        elif self.action in ['block','retrieve', 'list']:
            return [IsSupportOrCardOwner()]
        return super().get_permissions()

    def get_queryset(self):
        if self.action == 'list_admin_cards':
            return CreditCard.objects.all()
        if self.request.user.is_staff or getattr(self.request.user,'is_support', False):
            return CreditCard.objects.all()
        return CreditCard.objects.filter(user=self.request.user, status__in=['active', 'frozen'])
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CreditCard.DoesNotExist:
            return Response({"error": "Card not found"},status=status.HTTP_404_NOT_FOUND)
    
    def list(self, request,*args,**kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

    @action(detail=False, methods=['post'])
    @csrf_exempt
    @swagger_auto_schema(responses={201: "Card created successfully", 202: "Card request queued for approval"})
    def create_card(self, request):
        serializer = CardCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            card_type = serializer.validated_data['card_type']
            is_single_use = serializer.validated_data['is_single_use']
            income = serializer.validated_data['income']


            user.income = income
            user.save()

            credit_limit = calculate_credit_limit(card_type, user)

            if card_type.requires_admin_approval:
                card_request = CardRequest.objects.create(
                    user=user,
                    card_type=card_type,
                    is_single_use=is_single_use,
                    income=income,
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
                    credit_limit=credit_limit,
                    available_credit=credit_limit,
                    is_single_use=is_single_use
                )
                return Response(
                    CreditCardSerializer(card, context={'request':request}).data,
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
            
            credit_limit = calculate_credit_limit(card_request.card_type, card_request.user)
            card_number, hashed_number = generate_card_number()
            card = CreditCard.objects.create(
                user=card_request.user,
                card_type=card_request.card_type,
                card_number=hashed_number,
                cvv=make_password(generate_cvv()),
                expiry_date=calculate_expiry_date(card_request.card_type),
                credit_limit=credit_limit,
                available_credit=credit_limit,
                is_single_use=card_request.is_single_use
            )
            card_request.status = 'approved'
            card_request.save()
            return Response(
                CreditCardSerializer(card,context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except CardRequest.DoesNotExist:
            return Response({"error": "Card request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            from sentry_sdk import capture_exception
            capture_exception(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'])
    @swagger_auto_schema(responses={200: "Card frozen successfully"})
    def freeze(self, request, pk=None):
        try:
            card = self.get_object()
            if card.status == 'frozen':
                return Response({"error": "Card is already frozen"}, status=status.HTTP_400_BAD_REQUEST)
            if card.status == 'blocked':
                return Response({"error": "Blocked card cannot be frozen"}, status=status.HTTP_400_BAD_REQUEST)
            card.status = 'frozen'
            card.updated_at = timezone.now()
            card.save()
            return Response({"message": "Card frozen successfully"}, status=status.HTTP_200_OK)
        except CreditCard.DoesNotExist:
            return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    @swagger_auto_schema(responses={200: "Card unfrozen successfully"})
    def unfreeze(self, request, pk=None):
        try:
            card = self.get_object()
            if card.status== 'active':
                return Response({"error":"card is already active"}, status=status.HTTP_400_BAD_REQUEST)
            if card.status == 'blocked':
                return Response({"error": "Blocked card cannot be unfrozen"}, status=status.HTTP_400_BAD_REQUEST)
            card.status = 'active'
            card.updated_at = timezone.now()
            card.save()
            return Response({"message": "Card unfrozen successfully"}, status=status.HTTP_200_OK)
        except CreditCard.DoesNotExist:
            return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    @swagger_auto_schema(responses={200: "Card blocked successfully"})
    def block(self, request, pk=None):
        try:
            card = self.get_object()
            if card.status == 'blocked':
                return Response({"error": "Card is already blocked"}, status=status.HTTP_400_BAD_REQUEST)
            card.status = 'blocked'
            card.updated_at = timezone.now()
            card.save()
            return Response({"message": "Card blocked successfully"}, status=status.HTTP_200_OK)
        except CreditCard.DoesNotExist:
            return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    @swagger_auto_schema(responses={200: "Card unblocked successfully"})
    def unblock(self, request, pk=None):
        try:
            card = self.get_object()
            if card.status != 'blocked':
                return Response({"error": "Card is not blocked"}, status=status.HTTP_400_BAD_REQUEST)
            card.status = 'active'
            card.updated_at = timezone.now()
            card.save()
            return Response({"message": "Card Unblocked Successfully"}, status=status.HTTP_200_OK)
        except CreditCard.DoesNotExist:
            return Response({"error":"Card not found"}, status=status.HTTP_404_NOT_FOUND)
        

    @action(detail=False, methods=['get'],url_path='list_admin_cards')
    @swagger_auto_schema(responses={200: CreditCardSerializer(many=True)})
    def list_admin_cards(self, request):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True,context={'request': request, 'admin_view': True})
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True, context={'request': request, 'admin_view': True})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            from sentry_sdk import capture_exception
            capture_exception(e)
            return Response({"error": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        
