from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CardViewSet, SubscriptionViewSet
router = DefaultRouter()
router.register(r'', CardViewSet, basename='card')

subscription_router = DefaultRouter()
subscription_router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(subscription_router.urls)),
]

