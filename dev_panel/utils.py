import re
import time
import  logging
from django.db import connection, transaction
from django.conf import settings

logger = logging.getLogger("dev_panel")


BLOCKED_PATTERNS = [
    r"\bDROP\b",
    r"\bTRUNCATE\b",
    r"\bALTER\s+TABLE\b",
    r"\bCREATE\s+TABLE\b",
    r"\bDROP\s+DATABASE\b",
    r"\bPG_DUMP\b",
    r"\bCOPY\b",         
    r"--.*$", 
]

# RAW_SQL_EXTRA_BLOCKED = [
#     r"\bUPDATE\b",
#     r"\bINSERT\b",
#     r"\bDELETE\b",
# ]
 

def is_safe_query(sql: str) -> tuple[bool,str]:
    upper = sql.upper().strip()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, upper,re.MULTILINE):
            return False, f"blocked pattern detected: {pattern}"
    return True, ""

def get_all_tables() -> list[dict]:
    """
    Dynamically fetches all user tables from the public schema.
    No hardcoded whitelist — any newly migrated table appears automatically.
    """
    sql = """
        SELECT
            c.relname  AS name,
            c.reltuples::BIGINT AS rows,
            pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
            pg_total_relation_size(c.oid) AS size_bytes,
            (SELECT COUNT(*) FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = c.relname) AS columns,
             obj_description(c.oid) AS description
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY pg_total_relation_size(c.oid) DESC;
    """
    with connection.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def get_table_schema(table_name: str) -> list[dict]:
    _validate_table_name(table_name)
    sql = """
        SELECT
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            CASE WHEN kcu.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
        FROM information_schema.columns c
        LEFT JOIN information_schema.table_constraints tc
              ON tc.table_name = c.table_name
              AND tc.constraint_type = 'PRIMARY KEY' 
              AND tc.table_schema = 'public'
        LEFT JOIN information_schema.key_column_usage kcu
             ON kcu.constraint_name = tc.constraint_name
             AND kcu.column_name = c.column_name
        WHERE c.table_schema = 'public' AND c.table_name = %s
        ORDER BY c.ordinal_position;         
    """
    with connection.cursor() as cur:
        cur.execute(sql, [table_name])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]

def get_table_data(table_name: str, page=1, per_page=50, sort_col=None, sort_dir ='asc',search='') -> dict:
    _validate_table_name(table_name)
    schema = get_table_schema(table_name)
    if not schema:
        return {'rows': [], 'total':0, 'columns': []}
    available_cols = [c['column_name'] for c in schema]
    if sort_col is None or sort_col not in available_cols:
        sort_col = available_cols[0]
    _validate_identifier(sort_col)
    sort_dir = 'ASC' if sort_dir.lower() == 'asc' else 'DESC'
    offset = (page -1) * per_page

    # schema= get_table_schema(table_name)
    text_cols = [c['column_name'] for c in schema if 'char' in c['data_type'] or 'text' in c['data_type']]
    where = ""
    params: list = []

    if search and text_cols:
        clauses = [f'CAST("{col}" AS TEXT) ILIKE %s' for col in text_cols[:3]]
        where  =  "WHERE" + " OR ".join(clauses)
        params = [f"%{search}%"]* len(clauses)

    with connection.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}" {where}', params)
        total = cur.fetchone()[0]

    with connection.cursor() as cur:
        cur.execute(f'SELECT * FROM "{table_name}" {where} ORDER BY "{sort_col}" {sort_dir} LIMIT %s OFFSET %s', params + [per_page, offset])
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return {"rows": rows, "total": total, "columns": cols}

def insert_row(table_name: str,data: dict) -> dict:
    _validate_table_name(table_name)
    for k in data.keys():
        _validate_identifier(k)
    cols = [f'"{k}"' for k in data.keys()]
    placeholders = ["%s"] * len(data)
    sql = f'INSERT INTO "{table_name}" ({", ".join(cols)}) VALUES ({", ".join(placeholders)}) RETURNING *'
    with connection.cursor() as cur:
        cur.execute(sql, list(data.values()))
        row_cols = [d[0] for d in cur.description]
        row  = cur.fetchone()
    return dict(zip(row_cols, row))

def update_row(table_name: str , row_id: int , data: dict) -> dict:
    _validate_table_name(table_name)
    for k in data.keys():
        _validate_identifier(k)
    assignments = ",".join([f'"{k}" = %s' for k in data.keys()])
    sql = f'UPDATE "{table_name}" SET {assignments} WHERE id = %s RETURNING *'
    with connection.cursor() as cur:
        cur.execute(sql, list(data.values()) + [row_id])
        if cur.rowcount == 0:
            raise ValueError(f"Row  {row_id} not found in {table_name}")
        row_cols = [d[0] for d in cur.description]
        row = cur.fetchone()
    return dict(zip(row_cols,row))

def delete_row(table_name: str, row_id: int) -> bool:
    _validate_table_name(table_name)
    with connection.cursor() as cur:
        cur.execute(f'DELETE FROM "{table_name}" WHERE id = %s', [row_id])
        return cur.rowcount > 0



def get_db_stats() -> dict:
    with connection.cursor() as cur:
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cur.fetchone()[0]

        # Dynamically count all tables in the public schema
        cur.execute("""
            SELECT COUNT(*) FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
        """)
        table_count = cur.fetchone()[0]

        cur.execute("""
            SELECT COALESCE(SUM(reltuples::BIGINT),0)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
        """)
        total_rows = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
        active_conns = cur.fetchone()[0]

        cur.execute("""
            SELECT ROUND(
                    100.0 * SUM(blks_hit)/NULLIF(SUM(blks_hit) + SUM(blks_read), 0),2)
            FROM pg_stat_database
       """)
        cache_hit = cur.fetchone()[0] or 0
        slow_queries = 0

        try:
            cur.execute("SAVEPOINT sp_slow_queries")
            cur.execute("""
                SELECT COUNT(*) FROM pg_stat_statements
                        WHERE mean_exec_time > 500
            """)
            slow_queries = cur.fetchone()[0]
            cur.execute("RELEASE SAVEPOINT sp_slow_queries")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_slow_queries")
            
        return {
            "db_size": db_size,
            "table_count": table_count,
            "total_rows": total_rows,
            "active_conns": active_conns,
            "cache_hit_pct": float(cache_hit),
            "slow_queries": slow_queries,
        }
    
def run_raw_query(sql: str) -> dict:
    t0 = time.perf_counter()
    with connection.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        else:
            cols = []
            rows = []
        row_count = cur.rowcount if cur.rowcount != -1 else len(rows)
    
    exec_ms = int((time.perf_counter() - t0) * 1000)
    return {"columns": cols, "rows": rows, "exec_ms": exec_ms, "row_count": row_count}

def get_celery_tasks() -> dict:
    tasks = []
    with connection.cursor() as cur:
        cur.execute(""" SELECT pt.id,pt.name, pt.task,pt.enabled, pt.total_run_count, pt.last_run_at,pt.date_changed, pr.description, 
                    -- crontab schedule
                    CASE
                        WHEN pt.crontab_id IS NOT NULL THEN
                            cs.minute || ' ' || cs.hour || ' ' || cs.day_of_week
                        WHEN pt.interval_id IS NOT NULL THEN
                            'every' || ins.every || ins.period
                        ELSE 'custom'
                    END AS schedule_display,
                    CASE 
                        WHEN pt.crontab_id IS NOT NULL THEN 'crontab'
                        WHEN pt.interval_id IS NOT NULL THEN 'interval'
                        ElSE 'other'
                    END AS schedule_type
                    FROM django_celery_beat_periodictask pt
                    LEFT JOIN django_celery_beat_crontabschedule cs ON cs.id = pt.crontab_id
                    LEFT JOIN django_celery_beat_intervalschedule ins ON ins.id = pt.interval_id
                    ORDER BY pt.enabled DESC, pt.last_run_at DESC NULLS LAST 
        """)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        for row in rows:
            t = dict(zip(cols, row))
            tasks.append({
            "id": t["id"],
            "name": t["name"],
            "task": t["task"],
            "enabled": t["enabled"],
            "total_run_count": t["total_run_count"],
            "last_run_at": t["last_run_at"].isoformat() if t["last_run_at"] else None,
            "schedule": t["schedule_display"],
            "schedule_type": t["schedule_type"],
            "date_changed": t["date_changed"].isoformat() if t["date_changed"] else None,

            })
        return {
        "tasks": tasks,
        "total": len(tasks),
        "enabled_count": sum(1 for t in tasks if t["enabled"]),
        "disabled_count": sum(1 for t in tasks if not t["enabled"]),
        }

def trigger_celery_task(task_name: str) -> dict:
    from celery import current_app

    with connection.cursor() as cur:
        cur.execute("SELECT id, name FROM django_celery_beat_periodictask WHERE task = %s", [task_name])
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Task [{task_name}] not found in periodic task registry")
    
    result = current_app.send_task(task_name)
    return {
        "triggered": True,
        "task": task_name,
        "task_id": result.id,
    }

def get_migration_status() -> dict:
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(connection,ignore_no_migrations=True)

    with connection.cursor() as cur:
        cur.execute("""SELECT app,name, applied FROM django_migrations ORDER BY app, applied DESC""")
        rows = cur.fetchall()

    applied_by_app: dict = {}
    for app, name, applied_at in rows:
        if app not in applied_by_app:
            applied_by_app[app] = {"applied": [], "last_applied_at": None}
        applied_by_app[app]["applied"].append(name)
        if applied_by_app[app]["last_applied_at"] is None:
            applied_by_app[app]["last_applied_at"] = applied_at.isoformat() if applied_at else None
    
    applied_set = loader.applied_migrations
    pending_by_app: dict = {}
    for app_label, migration_name in loader.disk_migrations:
        if (app_label, migration_name) not in applied_set:
            if app_label not in pending_by_app:
                pending_by_app[app_label]  = []
            pending_by_app[app_label].append(migration_name)

    all_apps = sorted(set(list(applied_by_app.keys()) + list(pending_by_app.keys())))
    summary= []
    for app in all_apps:
        a = applied_by_app.get(app, {})
        p = pending_by_app.get(app, [])
        summary.append({
            "app": app,
            "applied_count": len(a.get("applied", [])),
            "pending_count": len(p),
            "pending": p,
            "last_applied_at": a.get("last_applied_at"),
        })
    
    total_applied = sum(len(a.get("applied", [])) for a in applied_by_app.values())
    total_pending = sum(len(p) for p in pending_by_app.values())

    return {
        "apps": summary,
        "total_applied": total_applied,
        "total_pending": total_pending,
        "has_pending": total_pending > 0,
    }


# SENTRY

def get_sentry_summary() -> dict:
    import re as _re
    import os
    import urllib.request
    import urllib.error
    import json

    dsn = getattr(settings, 'SENTRY_DSN', None)
    auth_token = getattr(settings, 'SENTRY_AUTH_TOKEN', None)
    # Fall back to os.environ directly in case django-environ didn't bind these
    org_slug = getattr(settings, 'SENTRY_ORG_SLUG', None) or os.environ.get('SENTRY_ORG_SLUG')
    project_slug = getattr(settings, 'SENTRY_PROJECT_SLUG', None) or os.environ.get('SENTRY_PROJECT_SLUG')

    if not dsn:
        return {"error": "SENTRY_DSN not configured in settings"}
    if not auth_token:
        return {"error": "SENTRY_AUTH_TOKEN not configured in settings. Required to fetch project stats."}
    if not org_slug:
        return {"error": "SENTRY_ORG_SLUG not configured — add it to .env and settings.py"}
    if not project_slug:
        return {"error": "SENTRY_PROJECT_SLUG not configured — add it to .env and settings.py"}

    match = _re.search(r'@([^/]+)/(\d+)$', dsn)
    if not match:
        return {"error": "Could not parse host from SENTRY_DSN. Expected format: https://key@host/project_id"}

    host = match.group(1)
    project_id = match.group(2)
    api_base = "https://sentry.io/api/0" if 'sentry.io' in host else f"https://{host}/api/0"

    def sentry_get(path):
        req = urllib.request.Request(
            f"{api_base}{path}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            return json.loads(resp.read())

    try:
        issues_data = sentry_get(
            f"/projects/{org_slug}/{project_slug}/issues/?query=is:unresolved&limit=10&sortBy=date"
        )
        issues = []
        for issue in issues_data:
            issues.append({
                "id": issue.get("id"),
                "title": issue.get("title"),
                "culprit": issue.get("culprit"),
                "level": issue.get("level"),
                "count": issue.get("count"),
                "user_count": issue.get("userCount"),
                "first_seen": issue.get("firstSeen"),
                "last_seen": issue.get("lastSeen"),
                "status": issue.get("status"),
                "url": issue.get("permalink"),
            })
        level_counts: dict = {}
        for i in issues:
            lvl = i["level"] or 'unknown'
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        return {
            "issues": issues,
            "total_shown": len(issues),
            "by_level": level_counts,
            "sentry_project_id": project_id,
            "sentry_org": org_slug,
            "sentry_project": project_slug,
        }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"error": "Sentry auth failed — check SENTRY_AUTH_TOKEN is valid and has read:issues scope"}
        if e.code == 403:
            return {"error": "Sentry token lacks permission — ensure it has read:issues scope"}
        return {"error": f"Sentry API returned {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Could not reach Sentry: {str(e.reason)}"}
    except Exception as e:
        logger.exception("Sentry fetch failed")
        return {"error": f"Unexpected error fetching Sentry data: {str(e)}"}

_SAFE_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_table_name(name: str):
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Invalid table name: {name}")
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = %s            
            """, [name]
        )
        if not cur.fetchone():
            raise ValueError(f"Table does not exist: {name}")

def _validate_identifier(name: str):
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Invalid column name: {name!r}")