from django.urls import path
from . import views

app_name = "dev_panel"

urlpatterns = [
    path("stats/", views.DevStatsView.as_view(), name="stats"),

    # ✅ specific routes FIRST
    path("tables/<str:table>/schema/", views.DevTableSchemaView.as_view(), name="table-schema"),
    path("tables/<str:table>/<int:pk>/", views.DevTableRowView.as_view(), name="table-row"),

    # ✅ then generic
    path("tables/<str:table>/", views.DevTableDataView.as_view(), name="table-data"),
    path("tables/", views.DevTableListView.as_view(), name="table-list"),

    path("query/", views.DevQueryView.as_view(), name="qury-run"),
    path("query/history/", views.DevQueryHistoryView.as_view(), name="query-history"),

    path("logs/", views.DevAuditLogView.as_view(), name="logs"),
    path("proxy/", views.DevProxyView.as_view(), name="proxy"),
]