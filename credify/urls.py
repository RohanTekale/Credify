from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static


schema_view = get_schema_view(
    openapi.Info(
        title="Credify API",
        default_version='v1',
        description="API for virtual credit card management",
        terms_of_service="https://www.credify.com/terms/",
        contact=openapi.Contact(email="support@credify.com"),
        license=openapi.License(name="MIT License"),

    ),
    public=True,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/users/', include('users.urls')),
    # path('api/cards/', include('cards.urls')),
    # path('api/transactions/', include('transactions.urls')),
    # path('api/billing/', include('billing.urls')),
    # path('api/rewards/', include('rewards.urls')),
    # path('api/notifications/', include('notifications.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
