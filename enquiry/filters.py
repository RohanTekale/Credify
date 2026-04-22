import django_filters
from .models import UserRequest
from django.db.models import Q


class EnquiryFilter(django_filters.FilterSet):
    status= django_filters.CharFilter(field_name='status',lookup_expr='exact')
    request_type = django_filters.CharFilter(field_name='request_type', lookup_expr='exact')
    priority = django_filters.CharFilter(field_name='priority',lookup_expr='exact')
    assigned_to =django_filters.NumberFilter(field_name='assigned_to__id')
    user_id = django_filters.NumberFilter(field_name='user__id')
    sla_breached=django_filters.BooleanFilter(field_name='sla_breached')
    date_from =django_filters.DateTimeFilter(field_name='created_at',lookup_expr='gte')
    date_to =django_filters.DateTimeFilter(field_name='created_at',lookup_expr='lte')
    search=django_filters.CharFilter(method='filter_search')

    def filter_search(self,queryset,name,value):
           return queryset.filter(
            Q(description__icontains=value) |
            Q(comments__body__icontains=value)
        ).distinct()
    
    class Meta:
        model=UserRequest
        fields=[
            'status', 'request_type', 'priority',
            'assigned_to', 'user_id', 'sla_breached',
            'date_from', 'date_to', 'search',
        ]