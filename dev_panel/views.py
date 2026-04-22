import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.test import RequestFactory
from django.urls import resolve
from .permissions import IsDevPanelUser
from .models import QueryLog, AuditLog
from . import utils

logger = logging.getLogger("dev_panel")


class DevPanelMixin:
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsDevPanelUser]

    def _audit(self, request, level, message, meta=""):
        try:
            AuditLog.objects.create(
                user=request.user,
                level=level,
                message=message,
                meta=meta,
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# DB STATS
# ─────────────────────────────────────────────────────────────────────────────

class DevStatsView(DevPanelMixin, APIView):
    def get(self, request):
        try:
            db_stats = utils.get_db_stats()
            query_count = QueryLog.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            error_count = QueryLog.objects.filter(
                success=False,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            return Response({**db_stats, "query_count_24h": query_count, "error_count_24h": error_count})
        except Exception as e:
            logger.exception("DevStatsView error")
            return Response({"error": str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# TABLE EXPLORER
# ─────────────────────────────────────────────────────────────────────────────

class DevTableListView(DevPanelMixin, APIView):
    def get(self, request):
        try:
            tables = utils.get_all_tables()
            self._audit(request, "INFO", "Listed all tables", "table-explorer")
            return Response({"tables": tables, "count": len(tables)})
        except Exception as e:
            logger.exception("DevTableListView error")
            return Response({"error": str(e)}, status=500)


class DevTableDataView(DevPanelMixin, APIView):
    def get(self, request, table):
        try:
            page = int(request.query_params.get("page", 1))
            per_page = min(int(request.query_params.get("per_page", 50)), 200)
            sort = request.query_params.get("sort", None)
            dir_ = request.query_params.get("dir", "asc")
            search = request.query_params.get("search", "")
            result = utils.get_table_data(table, page, per_page, sort, dir_, search)
            self._audit(request, "INFO", f"Browsed table: {table}", f"page={page}")
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("DevTableDataView GET error")
            return Response({"error": str(e)}, status=500)

    def post(self, request, table):
        try:
            data = request.data
            if not data:
                return Response({"error": "No data provided"}, status=400)
            row = utils.insert_row(table, data)
            self._audit(request, "INFO", f"INSERT into {table}", f"id={row.get('id')}")
            return Response({"row": row}, status=201)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("DevTableDataView POST error")
            return Response({"error": str(e)}, status=500)


class DevTableSchemaView(DevPanelMixin, APIView):
    def get(self, request, table):
        try:
            schema = utils.get_table_schema(table)
            return Response({"schema": schema})
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class DevTableRowView(DevPanelMixin, APIView):
    def put(self, request, table, pk):
        try:
            data = request.data
            if not data:
                return Response({"error": "No data provided"}, status=400)
            row = utils.update_row(table, pk, data)
            self._audit(request, "INFO", f"UPDATE {table} id={pk}", "crud")
            return Response({"row": row})
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("DevTableRowView PUT error")
            return Response({"error": str(e)}, status=500)

    def delete(self, request, table, pk):
        try:
            deleted = utils.delete_row(table, pk)
            if not deleted:
                return Response({"error": "Row not found"}, status=404)
            self._audit(request, "INFO", f"DELETE from {table} id={pk}", "crud")
            return Response({"deleted": True, "id": pk})
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("DevTableRowView DELETE error")
            return Response({"error": str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# SQL RUNNER
# ─────────────────────────────────────────────────────────────────────────────

class DevQueryView(DevPanelMixin, APIView):
    def post(self, request):
        sql = (request.data.get("query") or "").strip()
        if not sql:
            return Response({"error": "No query provided"}, status=400)
        safe, reason = utils.is_safe_query(sql)
        if not safe:
            AuditLog.objects.create(
                user=request.user, level="ERROR",
                message=f"BLOCKED query: {sql[:120]}", meta=reason
            )
            return Response({"error": f"Query blocked: {reason}"}, status=403)
        log = QueryLog(user=request.user, sql=sql)
        try:
            result = utils.run_raw_query(sql)
            log.exec_ms = result["exec_ms"]
            log.row_count = result["row_count"]
            log.success = True
            log.save()
            self._audit(request, "SQL", f"Query executed ({result['exec_ms']}ms, {result['row_count']} rows)", sql[:120])
            return Response(result)
        except Exception as e:
            log.success = False
            log.error_msg = str(e)
            log.save()
            self._audit(request, "ERROR", f"Query failed: {str(e)}", sql[:80])
            return Response({"error": str(e)}, status=400)


class DevQueryHistoryView(DevPanelMixin, APIView):
    def get(self, request):
        # ?all_users=true lets superusers see all queries, not just their own
        show_all = request.query_params.get("all_users", "false").lower() == "true"
        qs = QueryLog.objects.select_related("user").order_by("-created_at")
        if not show_all:
            qs = qs.filter(user=request.user)
        qs = qs[:100]
        data = [{
            "id": l.id,
            "user": l.user.email if l.user else "system",
            "sql": l.sql,
            "exec_ms": l.exec_ms,
            "row_count": l.row_count,
            "success": l.success,
            "error_msg": l.error_msg,
            "time": l.created_at.strftime("%H:%M:%S"),
            "date": l.created_at.strftime("%Y-%m-%d"),
        } for l in qs]
        return Response({"history": data})


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGS
# ─────────────────────────────────────────────────────────────────────────────

class DevAuditLogView(DevPanelMixin, APIView):
    def get(self, request):
        level = request.query_params.get("level", "")
        search = request.query_params.get("search", "")
        limit = min(int(request.query_params.get("limit", 100)), 500)
        qs = AuditLog.objects.select_related("user")
        if level and level != 'ALL':
            qs = qs.filter(level=level)
        if search:
            qs = qs.filter(message__icontains=search)
        logs = qs[:limit]
        data = [{
            "id": l.id,
            "user": l.user.email if l.user else "system",
            "level": l.level,
            "msg": l.message,
            "meta": l.meta,
            "time": l.created_at.strftime("%H:%M:%S"),
            "date": l.created_at.strftime("%Y-%m-%d"),
        } for l in logs]
        counts = {lvl: AuditLog.objects.filter(level=lvl).count() for lvl, _ in AuditLog.LEVELS}
        return Response({"logs": data, "counts": counts})


 
# ─────────────────────────────────────────────────────────────────────────────
# CELERY TASK MONITOR
# ─────────────────────────────────────────────────────────────────────────────\

class DevTaskListView(DevPanelMixin, APIView):
    def get(self,request):
        try:
            data = utils.get_celery_tasks()
            self._audit(request, "INFO", "Viewed Celery Task List","tasks")
            return Response(data)
        except Exception as e:
            logger.exception("DevTaskListView error")
            return Response({"error": str(e)}, status=500)
        
class DevTaskTriggerView(DevPanelMixin,APIView):
    def post(self,request):
        task_name = (request.data.get("task") or "").strip()
        if not task_name:
            return Response({"error": "No task name provided"}, status=400)
        try:
            result = utils.trigger_celery_task(task_name)
            self._audit(request,"WARN", f"Manually triggered task: {task_name}", "tasks")
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("DevTaskTriggerView error")
            return Response({"error": str(e)}, status=500)

# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION STATUS
# ─────────────────────────────────────────────────────────────────────────────
 
class DevMigrationView(DevPanelMixin,APIView):
    def get(self,request):
        try:
            data = utils.get_migration_status()
            self._audit(request,"INFO", "Viewed migration status", "migrations")
            return Response(data)
        except Exception as e:
            logger.exception("DevMigrationView error")
            return Response({"error": str(e)}, status=500)

 
# ─────────────────────────────────────────────────────────────────────────────
# SENTRY FEED
# ─────────────────────────────────────────────────────────────────────────────

class DevSentryView(DevPanelMixin,APIView):
    def get(self,request):
        try:
            data =utils.get_sentry_summary()
            self._audit(request,"INFO", "Viewed Sentry issues", "sentry")
            return Response(data)
        except Exception as e:
            logger.exception("DevSentryView error")
            return Response({"error": str(e)}, status=500)
# # ─────────────────────────────────────────────────────────────────────────────
# # API PROXY / DEBUGGER
# # ─────────────────────────────────────────────────────────────────────────────

@transaction.non_atomic_requests
class DevProxyView(DevPanelMixin, APIView):
    def post(self, request):
        method = (request.data.get("method") or "GET").upper()
        path = request.data.get("path") or "/"
        body = request.data.get("body")

        allowed_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if method not in allowed_methods:
            return Response({"error": f"Method {method} not allowed"}, status=400)

        factory = RequestFactory()
        django_request = getattr(factory, method.lower())(
            path, data=body, content_type="application/json"
        )
        django_request.user = request.user
        django_request.META["HTTP_AUTHORIZATION"] = request.META.get("HTTP_AUTHORIZATION", "")

        try:
            resolver_match = resolve(path)
            response = resolver_match.func(django_request, *resolver_match.args, **resolver_match.kwargs)
            if hasattr(response, "render"):
                response = response.render()
            body_out = response.data if hasattr(response, "data") else response.content.decode("utf-8")
            return Response({"status": response.status_code, "body": body_out})
        except Exception as e:
            return Response({"error": str(e)}, status=500)