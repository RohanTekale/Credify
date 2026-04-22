from django.urls import path
from . import views

app_name = "dev_panel"

urlpatterns = [

    # ── Infra snapshots ───────────────────────────────────────────────────────
    path("stats/",       views.DevStatsView.as_view(),       name="stats"),
    path("migrations/",  views.DevMigrationView.as_view(),   name="migrations"),
    path("sentry/",      views.DevSentryView.as_view(),      name="sentry"),

    # # ── Phase 2 — system visibility ───────────────────────────────────────────
    # path("cache/",       views.DevRedisView.as_view(),       name="cache"),
    # path("config/",      views.DevConfigView.as_view(),      name="config"),
    # path("indexes/",     views.DevIndexHealthView.as_view(), name="indexes"),

    # ── Celery task monitor ───────────────────────────────────────────────────
    path("tasks/",         views.DevTaskListView.as_view(),    name="task-list"),
    path("tasks/trigger/", views.DevTaskTriggerView.as_view(), name="task-trigger"),

    # ── Table explorer (specific routes before generic) ───────────────────────
    path("tables/<str:table>/schema/",   views.DevTableSchemaView.as_view(), name="table-schema"),
    path("tables/<str:table>/<int:pk>/", views.DevTableRowView.as_view(),    name="table-row"),
    path("tables/<str:table>/",          views.DevTableDataView.as_view(),   name="table-data"),
    path("tables/",                      views.DevTableListView.as_view(),   name="table-list"),

    # ── SQL runner ────────────────────────────────────────────────────────────
    path("query/",         views.DevQueryView.as_view(),        name="query-run"),
    path("query/history/", views.DevQueryHistoryView.as_view(), name="query-history"),

    # ── Logs & proxy ──────────────────────────────────────────────────────────
    path("logs/",  views.DevAuditLogView.as_view(), name="logs"),
    path("proxy/", views.DevProxyView.as_view(),    name="proxy"),
]