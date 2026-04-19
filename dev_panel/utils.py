import re
import time
import  logging
from django.db import connection, transaction

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

def get_table_data(table_name: str, page=1, per_page=50, sort_col='id', sort_dir ='asc',search='') -> dict:
    _validate_table_name(table_name)
    _validate_identifier(sort_col)
    sort_dir = 'ASC' if sort_dir.lower() == 'asc' else 'DESC'
    offset = (page -1) * per_page

    schema= get_table_schema(table_name)
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

    data_sql = f'''
        SELECT * FROM "{table_name}"
        {where}
        ORDER BY  "{sort_col}" {sort_dir}
        LIMIT %s OFFSET %s
    '''
    with connection.cursor() as cur:
        cur.execute(data_sql, params + [per_page, offset])
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return {"rows": rows, "total": total, "columns": cols}

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

def insert_row(table_name: str,data: dict) -> dict:
    _validate_table_name(table_name)
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

_SAFE_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_table_name(name: str):
    """
    Validates table name against actual DB tables in the public schema.
    No hardcoded whitelist — works automatically with any migrated table.
    """
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