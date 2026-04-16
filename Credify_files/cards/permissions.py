from rest_framework import permissions
from .models import CreditCard
from users.permissions import IsSupportStaff


class IsSupportOrCardOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):

        if IsSupportStaff().has_permission(request,view):
            return True
        
        return obj.user == request.user
        
 