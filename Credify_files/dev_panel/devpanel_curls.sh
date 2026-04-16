# Credify Dev Panel — Complete cURL Reference
# Base URL: http://localhost:8080
# All endpoints require: Authorization: Bearer <admin_access_token>
# 
# HOW TO GET YOUR TOKEN:
# First run the login curl at the top, then copy the access token
# and export it: export TOKEN="your_token_here"
# Then all other curls use $TOKEN automatically.
# ─────────────────────────────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════════
# STEP 0 — GET ADMIN TOKEN (run this first)
# ════════════════════════════════════════════════════════════════════════════

curl -s -X POST http://localhost:8080/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@credify",
    "password": "Credifyadmin@00715"
  }' | python3 -m json.tool

# Then export the access token:
# export TOKEN="paste_your_access_token_here"


# ════════════════════════════════════════════════════════════════════════════
# 1. STATS — GET /api/dev/stats/
# ════════════════════════════════════════════════════════════════════════════
# Returns: DB size, table count, total rows, cache hit %, slow queries, 24h query count

curl -s -X GET http://localhost:8080/api/dev/stats/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 2. TABLES — GET /api/dev/tables/
# ════════════════════════════════════════════════════════════════════════════
# Returns: all PostgreSQL public tables with row counts and sizes

curl -s -X GET http://localhost:8080/api/dev/tables/ \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 3. TABLE DATA — GET /api/dev/tables/<table>/
# ════════════════════════════════════════════════════════════════════════════
# Returns: paginated rows for a specific table

# Basic (first page, default 50 rows):
curl -s -X GET "http://localhost:8080/api/dev/tables/users/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# With pagination:
curl -s -X GET "http://localhost:8080/api/dev/tables/users/?page=2&per_page=20" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# With sorting (sort by created_at descending):
curl -s -X GET "http://localhost:8080/api/dev/tables/users/?sort=created_at&dir=desc" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# With search filter:
curl -s -X GET "http://localhost:8080/api/dev/tables/users/?search=admin" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Combined — page 1, 10 per page, sort by id desc, search "anjali":
curl -s -X GET "http://localhost:8080/api/dev/tables/users/?page=1&per_page=10&sort=id&dir=desc&search=anjali" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Other tables (replace 'users' with any table name):
curl -s -X GET "http://localhost:8080/api/dev/tables/cards/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/transactions/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/auth_tokens/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/kyc_documents/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/notifications/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/audit_logs/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 4. TABLE SCHEMA — GET /api/dev/tables/<table>/schema/
# ════════════════════════════════════════════════════════════════════════════
# Returns: column names, data types, nullability, primary key info

curl -s -X GET "http://localhost:8080/api/dev/tables/users/schema/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/cards/schema/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

curl -s -X GET "http://localhost:8080/api/dev/tables/transactions/schema/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 5. CREATE ROW — POST /api/dev/tables/<table>/
# ════════════════════════════════════════════════════════════════════════════
# Insert a new row into any table

# Insert into notifications:
curl -s -X POST "http://localhost:8080/api/dev/tables/notifications/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "Test notification from Dev Panel",
    "is_read": false
  }' | python3 -m json.tool

# Insert into audit_logs (if you have such a table):
curl -s -X POST "http://localhost:8080/api/dev/tables/audit_logs/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "action": "manual_insert",
    "details": "Inserted via dev panel curl test"
  }' | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 6. UPDATE ROW — PUT /api/dev/tables/<table>/<id>/
# ════════════════════════════════════════════════════════════════════════════
# Update specific fields of a row by its primary key (id)

# Update user with id=5:
curl -s -X PUT "http://localhost:8080/api/dev/tables/users/5/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Updated via Dev Panel - Pune, India"
  }' | python3 -m json.tool

# Update a card status:
curl -s -X PUT "http://localhost:8080/api/dev/tables/cards/3/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }' | python3 -m json.tool

# Update multiple fields at once:
curl -s -X PUT "http://localhost:8080/api/dev/tables/users/2/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "9876543210",
    "address": "Mumbai, Maharashtra"
  }' | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 7. DELETE ROW — DELETE /api/dev/tables/<table>/<id>/
# ════════════════════════════════════════════════════════════════════════════
# Permanently delete a row by primary key

# Delete notification with id=10:
curl -s -X DELETE "http://localhost:8080/api/dev/tables/notifications/10/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Delete a session record:
curl -s -X DELETE "http://localhost:8080/api/dev/tables/sessions/7/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 8. SQL QUERY RUNNER — POST /api/dev/query/
# ════════════════════════════════════════════════════════════════════════════
# Execute raw SQL queries (blocked: DROP, TRUNCATE, ALTER, CREATE TABLE, COPY)

# SELECT all users:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT id, username, email, is_active, kyc_status FROM users_user ORDER BY id DESC LIMIT 10"
  }' | python3 -m json.tool

# COUNT rows per table:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT schemaname, tablename, n_live_tup AS row_count FROM pg_stat_user_tables ORDER BY n_live_tup DESC"
  }' | python3 -m json.tool

# Transaction stats by status:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT status, COUNT(*) as count, SUM(amount) as total FROM transactions_transaction GROUP BY status ORDER BY total DESC"
  }' | python3 -m json.tool

# JOIN query — users with their card count:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT u.id, u.username, u.email, COUNT(c.id) as card_count FROM users_user u LEFT JOIN cards_card c ON c.user_id = u.id GROUP BY u.id, u.username, u.email ORDER BY card_count DESC LIMIT 20"
  }' | python3 -m json.tool

# Active cards with holder info:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT c.id, c.card_type, c.status, c.credit_limit, u.email FROM cards_card c JOIN users_user u ON u.id = c.user_id WHERE c.status = '\''active'\'' ORDER BY c.credit_limit DESC"
  }' | python3 -m json.tool

# KYC status breakdown:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT kyc_status, COUNT(*) as count FROM users_user GROUP BY kyc_status"
  }' | python3 -m json.tool

# Recent transactions (last 24 hours):
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM transactions_transaction WHERE created_at >= NOW() - INTERVAL '\''24 hours'\'' ORDER BY created_at DESC"
  }' | python3 -m json.tool

# Database size info:
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC"
  }' | python3 -m json.tool

# Update via SQL (use carefully):
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "UPDATE users_user SET is_active = true WHERE id = 5 RETURNING id, username, is_active"
  }' | python3 -m json.tool

# Test BLOCKED query (should return 403):
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DROP TABLE users_user"
  }' | python3 -m json.tool

# Test BLOCKED truncate (should return 403):
curl -s -X POST "http://localhost:8080/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "TRUNCATE TABLE sessions"
  }' | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 9. QUERY HISTORY — GET /api/dev/query/history/
# ════════════════════════════════════════════════════════════════════════════
# Returns: last 50 SQL queries run by the current admin user

curl -s -X GET "http://localhost:8080/api/dev/query/history/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 10. AUDIT LOGS — GET /api/dev/logs/
# ════════════════════════════════════════════════════════════════════════════
# Returns: system audit log entries

# All logs (default 100):
curl -s -X GET "http://localhost:8080/api/dev/logs/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Filter by level — INFO only:
curl -s -X GET "http://localhost:8080/api/dev/logs/?level=INFO" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Filter — ERROR only:
curl -s -X GET "http://localhost:8080/api/dev/logs/?level=ERROR" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Filter — SQL queries only:
curl -s -X GET "http://localhost:8080/api/dev/logs/?level=SQL" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Filter — WARN only:
curl -s -X GET "http://localhost:8080/api/dev/logs/?level=WARN" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Search by message content:
curl -s -X GET "http://localhost:8080/api/dev/logs/?search=DELETE" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Combined — ERROR level, last 20 entries:
curl -s -X GET "http://localhost:8080/api/dev/logs/?level=ERROR&limit=20" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Max entries (500):
curl -s -X GET "http://localhost:8080/api/dev/logs/?limit=500" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# 11. API PROXY / DEBUGGER — POST /api/dev/proxy/
# ════════════════════════════════════════════════════════════════════════════
# Proxy requests to internal Django endpoints for debugging
# Your JWT is auto-injected, so proxied requests are authenticated

# Proxy GET /api/users/ (list all users):
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/users/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy GET /api/users/profile:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/users/profile",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy GET /api/cards/:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/cards/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy GET /api/cards/list_admin_cards/:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/cards/list_admin_cards/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy GET /api/transactions/:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/api/transactions/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy POST — run a KYC review:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "POST",
    "path": "/api/users/kyc_review/",
    "body": {
      "user_id": 5,
      "kyc_status": "verified",
      "reviewer_comments": "Document is valid"
    },
    "headers": {}
  }' | python3 -m json.tool

# Proxy PATCH — freeze a card:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "PATCH",
    "path": "/api/cards/6/freeze/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool

# Proxy DELETE — deactivate user:
curl -s -X POST "http://localhost:8080/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "DELETE",
    "path": "/api/users/3/",
    "body": null,
    "headers": {}
  }' | python3 -m json.tool


# ════════════════════════════════════════════════════════════════════════════
# QUICK TEST SCRIPT — run all in sequence
# ════════════════════════════════════════════════════════════════════════════
# Copy-paste this entire block into your terminal to verify all endpoints work:

BASE="http://localhost:8080"
TOKEN="paste_your_admin_token_here"

echo ""
echo "=== 1. STATS ==="
curl -s "$BASE/api/dev/stats/" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 2. TABLE LIST ==="
curl -s "$BASE/api/dev/tables/" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 3. TABLE DATA (users) ==="
curl -s "$BASE/api/dev/tables/users/?per_page=3" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 4. SCHEMA (users) ==="
curl -s "$BASE/api/dev/tables/users/schema/" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 5. SQL QUERY ==="
curl -s -X POST "$BASE/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) as total_users FROM users_user"}' | python3 -m json.tool

echo ""
echo "=== 6. QUERY HISTORY ==="
curl -s "$BASE/api/dev/query/history/" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 7. AUDIT LOGS ==="
curl -s "$BASE/api/dev/logs/?limit=5" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "=== 8. BLOCKED QUERY TEST ==="
curl -s -X POST "$BASE/api/dev/query/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "DROP TABLE users_user"}' | python3 -m json.tool

echo ""
echo "=== 9. PROXY (users list) ==="
curl -s -X POST "$BASE/api/dev/proxy/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"method": "GET", "path": "/api/users/", "body": null, "headers": {}}' | python3 -m json.tool

echo ""
echo "All dev panel endpoints tested!"
