from rest_framework.permissions import BasePermission

class IsDevPanelUser(BasePermission):
    message = "Dev Panel access is restricted to admin/staff users only."

    def has_permission(self, request, view):
        return bool (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )