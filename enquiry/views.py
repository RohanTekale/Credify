from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import cloudinary.uploader
from users.permissions import IsSupportStaff
from .models import UserRequest
from .serializers import ( RaiseRequestSerializer, UserRequestListSerializer, AdminRequestListSerializer, AdminActionSerializer,UserCommentSerializer, DocumentUploadSerializer)
from .tasks import send_request_status_email



class UserRequestViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser,parsers.JSONParser,parsers.FormParser]


    @action(detail=False, methods=['post'], url_path='raise')
    def raise_request(self, request):
        serializer = RaiseRequestSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():
            req = serializer.save()
            return Response({"message": "Request raised successfully", "request_id": f"REQ-{req.id}", "status": req.status,}, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_requests(self, request):
        qs = UserRequest.objects.filter(user=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = UserRequestListSerializer(qs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='comment')
    def add_user_comment(self, request,pk=None):
        try:
            req = UserRequest.objects.get(pk=pk, user=request.user)
        except UserRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserCommentSerializer(data=request.data)
        if serializer.is_valid():
            req.user_comment = serializer.validated_data['user_comment']
            req.save()
            return Response({"message": "Comment added successfully"})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='document')
    def upload_document(self, request, pk=None):
        try:
            req = UserRequest.objects.get(pk=pk, user=request.user)
        except UserRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['document']
            result = cloudinary.uploader.upload(file, folder = 'request_documents', resource_type='auto')
            req.document = result['secure_url']
            req.save()
            return Response({"message": "Document uploaded successfully", "document_url": req.document})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True,methods=['post'], url_path='reraise')
    def reraise_request(self, request, pk=None):
        try:
            original = UserRequest.objects.get(pk=pk,user=request.user, status='rejected')
        except UserRequest.DoesNotExist:
            return Response({"error": "Only your rejected requests can be re-raised."}, status=status.HTTP_404_NOT_FOUND)
        new_req = UserRequest.objects.create(user=request.user, request_type=original.request_type, description=original.description, parent_request=original)
        return Response({"message": "Request re-raised successfully", "request_id": f"REQ-{new_req.id}", "status": new_req.status}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='admin', permission_classes=[IsSupportStaff])
    def admin_list(self, request):
        qs = UserRequest.objects.select_related('user').all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = AdminRequestListSerializer(qs,many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'],url_path='action',permission_classes=[IsSupportStaff])
    def admin_action(self, request,pk=None):
        try:
            req = UserRequest.objects.get(pk=pk)
        except UserRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminActionSerializer(data=request.data)
        if serializer.is_valid():
            req.status = serializer.validated_data['status']
            req.admin_comment = serializer.validated_data.get('admin_comment', '')
            req.save()
            send_request_status_email.delay(req.user.email,f"REQ-{req.id}",req.request_type,req.status,req.admin_comment)
            return Response({"message": f"Request {req.status}."})
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'],url_path='document', permission_classes=[IsSupportStaff])
    def admin_view_document(self, request, pk=None):
        try:
            req = UserRequest.objects.get(pk=pk)
        except UserRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        if not req.document:
            return Response({"document": None, "message": "No document uploaded for this request."})
        return Response({"document": req.document})




        


