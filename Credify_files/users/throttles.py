from rest_framework.throttling import AnonRateThrottle

class RequestReactivationOnlyThrottle(AnonRateThrottle):
    def allow_request(self, request, view):
         action = getattr(view,"action", None)
         if action == 'request_activation':
            return super().allow_request(request, view)
         return True