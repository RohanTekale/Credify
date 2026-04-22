import cloudinary.uploader
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsSupportStaff
from .models import UserRequest,EnquiryComment,EnquiryStatusLog
from .serializers import (
    RaiseRequestSerializer,
    UserRequestListSerializer,
    UserRequestDetailSerializer,
    AdminRequestListSerializer,
    AdminRequestDetailSerializer,
    AdminActionSerializer,
    AssignRequestSerializer,
    AdminCommentSerializer,
    UserCommentSerializer,
    DocumentUploadSerializer,
    RatingSerializer,
)
from .tasks import send_request_status_email
from .filters import EnquiryFilter


User = get_user_model()

class EnquiryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

def _get_request_or_404(pk, user=None):
    qs = UserRequest.objects.select_related('user', 'assigned_to')
    if user:
        qs = qs.filter(user=user)
    try:
        return qs.get(pk=pk), None
    except UserRequest.DoesNotExist:
        return None,Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

class UserRequestViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser,parsers.JSONParser,parsers.FormParser]
    pagination_class = EnquiryPagination


    @action(detail=False, methods=['post'], url_path='raise')
    def raise_request(self, request):
        serializer = RaiseRequestSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():
            req = serializer.save()
            return Response({"message": "Request raised successfully", "request_id": f"REQ-{req.id}", "status": req.status,'priority': req.priority, 'sla_deadline': req.sla_deadline}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_requests(self, request):
        qs = UserRequest.objects.select_related('user','assigned_to').prefetch_related('comments','history')
        status_filter = request.query_params.get('status')
        type_filter = request.query_params.get('request_type')
        priority_filter = request.query_params.get('priority')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(request_type =type_filter)
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = UserRequestListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(UserRequestListSerializer(qs, many=True).data)
    
    @action(detail=True,methods=['get'],url_path='detail')
    def my_request_detail(self,request, pk=None):
        req,err = _get_request_or_404(pk, user=request.user)
        if err:
            return err
        if not req.is_viewed_by_user:
            req.is_viewed_by_user=True
            req.save(update_fields=['is_viewed_by_user'])
        return Response(UserRequestDetailSerializer(req).data)
    
    @action(detail=True, methods=['post'], url_path='comment')
    def add_user_comment(self, request,pk=None):
        req,err = _get_request_or_404(pk,user=request.user)
        if err:
            return err
        serializer = UserCommentSerializer(data=request.data)
        if serializer.is_valid():
            EnquiryComment.objects.create(enquiry=req,author=request.user,body=serializer.validated_data['user_comment'], is_internal=False,)
            req.is_viewed_by_user=False
            req.save(update_fields=["is_viewed_by_user"])
            return Response({"message": "Comment added successfully"})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='document')
    def upload_document(self, request, pk=None):
        req,err = _get_request_or_404(pk, user=request.user)
        if err:
            return err
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['document']
            result = cloudinary.uploader.upload(file, folder = 'request_documents', resource_type='auto')
            req.document = result['secure_url']
            req.save(update_fields=["document"])
            return Response({"message": "Document uploaded successfully", "document_url": req.document})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True,methods=['post'],url_path='rate')
    def rate_request(self,request,pk=None):
        req,err = _get_request_or_404(pk,user=request.user)
        if err:
            return err
        if req.status != 'completed':
            return Response({'error': 'You can only rate a completed request.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = RatingSerializer(data=request.data)
        if serializer.is_valid():
            req.user_rating = serializer.validated_data['user_rating']
            req.user_feedback = serializer.validated_data.get('user_feedback', '')
            req.save(update_fields=['user_rating','user_feedback'])
            return Response({'message':'Thank You for your feedback'})
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True,methods=['post'],url_path='reraise')
    def reraise_request(self,request,pk=None):
        req,err = _get_request_or_404(pk,user=request.user)
        if err:
            return err
        if req.status !='rejected':
            return Response({'error':'Only rejected requests can be re-raised.' },status=status.HTTP_400_BAD_REQUEST)
        new_req = UserRequest(user=request.user,request_type=req.request_type,description=request.data.get('description',req.description),priority=req.priority,parent_request=req,)
        new_req.save()
        return Response({'message':    'Request re-raised.', 'request_id': f'REQ-{new_req.id}'},status=status.HTTP_201_CREATED)
        
    
    @action(detail=False, methods=['get'], url_path='admin', permission_classes=[IsSupportStaff])
    def admin_list(self, request):
        qs = UserRequest.objects.select_related('user','assigned_to').prefetch_related('comments','history').all()
        filterset = EnquiryFilter(request.query_params,queryset=qs)
        if filterset.is_valid():
            qs=filterset.qs
        else:
            return Response({'error': filterset.errors},status=status.HTTP_400_BAD_REQUEST)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = AdminRequestListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(AdminRequestListSerializer(qs, many=True).data)
    
    @action(detail=True,methods=['get'],url_path='admin/detail',permission_classes=[IsSupportStaff])
    def admin_detail(self,request,pk=None):
        req,err =_get_request_or_404(pk)
        if err:
            return err
        return Response(AdminRequestDetailSerializer(req).data)

    @action(detail=True, methods=['post'],url_path='action',permission_classes=[IsSupportStaff])
    def admin_action(self, request,pk=None):
        req,err =_get_request_or_404(pk)
        if err:
            return err
        serializer = AdminActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error':serializer.errors},status=status.HTTP_400_BAD_REQUEST)
        old_status = req.status
        new_status = serializer.validated_data["status"]
        comment = serializer.validated_data.get('admin_comment','')
        is_internal = serializer.validated_data.get('is_internal', False)

        req.status = new_status
        if new_status in ('completed','rejected'):
            req.resolved_at = timezone.now()
        
        req.is_viewed_by_user = False
        req.save(update_fields = ['status','resolved_at','is_viewed_by_user'])
        
        EnquiryStatusLog.objects.create(enquiry=req,changed_by=request.user, old_status=old_status,new_status=new_status,comment=comment if not is_internal else '[internal]' )
        if comment:
            EnquiryComment.objects.create(enquiry=req,author=request.user,body=comment,is_internal=is_internal,)
        if not is_internal:
            send_request_status_email.delay(req.user.email,f'REQ-{req.id}',req.request_type,new_status,comment,)
        
        return Response({'message': f'Request marked as {new_status}. '})
    
    @action(detail=True,methods=['post'],url_path='admin/comment',permission_classes=[IsSupportStaff])
    def admin_comment(self,request,pk=None):
        req,err = _get_request_or_404(pk)
        if err:
            return err
        serializer= AdminCommentSerializer(data=request.data)
        if serializer.is_valid():
            is_internal = serializer.validated_data.get('is_internal',False)
            EnquiryComment.objects.create(enquiry=req,author=request.user,body=serializer.validated_data['body'],is_internal=is_internal)
            if not is_internal:
                req.is_viewed_by_user =False
                req.save(update_fields=['is_viewed_by_user'])
            return Response({'message':'Comment added.'})
        return Response({'error': serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True,methods=['post'],url_path='assign',permission_classes=[IsSupportStaff])
    def assign_request(self,request,pk=None):
        req,err = _get_request_or_404(pk)
        if err:
            return err
        serializer=AssignRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error':serializer.errors},status=status.HTTP_400_BAD_REQUEST)
        try:
            agent = User.objects.get(pk=serializer.validated_data['assigned_to'],is_support=True)
        except User.DoesNotExist:
            return Response({'error':'Support agent not found'},status=status.HTTP_404_NOT_FOUND)
        
        req.assigned_to=agent
        req.assigned_at =timezone.now()
        req.save(update_fields=['assigned_to','assigned_at'])
        return Response({'message':f'Request assigned to {agent.username}.'})
    
    @action(detail=True,methods=['delete'],url_path='archive',permission_classes=[IsSupportStaff])
    def archive_request(self,request,pk=None):
        req,err = _get_request_or_404(pk)
        if err:
            return err
        req.soft_delete()
        return Response({"message": f'REQ-{req.id} archived'})

    @action(detail=True, methods=['get'],url_path='admin/document', permission_classes=[IsSupportStaff])
    def admin_view_document(self, request, pk=None):
        req,err = _get_request_or_404(pk)
        if err:
            return err
        if not req.document:
            return Response({"document": None, "message": "No document uploaded for this request."})
        return Response({"document": req.document})




        


