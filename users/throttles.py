from rest_framework.throttling import AnonRateThrottle

class RequestReactivationOnlyThrottle(AnonRateThrottle):
    def allow_request(self, request, view):
      if view.action == 'request_reactivation':
         return super().allow_request(request, view)
      return True