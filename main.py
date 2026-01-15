from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
import sqlite3, os, hmac, hashlib, time, json, uuid
from datetime import datetime
from typing import Optional, List

# ---------- CONFIG ----------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    raise RuntimeError("WEBHOOK_SECRET not set")

DB_PATH = "/data/app.db"

# ---------- APP ----------
app = FastAPI()

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def startup():
    os.makedirs("/data", exist_ok=True)
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            from_msisdn TEXT NOT NULL,
            to_msisdn TEXT NOT NULL,
            ts TEXT NOT NULL,
            text TEXT,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# ---------- LOGGING ----------
def log(request, status, start, extra=None):
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "request_id": str(uuid.uuid4()),
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "latency_ms": int((time.time() - start) * 1000)
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload))

# ---------- METRICS ----------
HTTP_METRICS = {}
WEBHOOK_METRICS = {}

def inc_http(path, status):
    key = (path, status)
    HTTP_METRICS[key] = HTTP_METRICS.get(key, 0) + 1

def inc_webhook(result):
    WEBHOOK_METRICS[result] = WEBHOOK_METRICS.get(result, 0) + 1

# ---------- MODELS ----------
class WebhookMessage(BaseModel):
    message_id: str = Field(min_length=1)
    from_: str = Field(alias="from", pattern=r"^\+\d+$")
    to: str = Field(pattern=r"^\+\d+$")
    ts: str
    text: Optional[str] = Field(default=None, max_length=4096)

    ts: str
    text: Optional[str] = Field(default=None, max_length=4096)

    ts: str
    text: Optional[str] = Field(default=None, max_length=4096)

# ---------- ENDPOINTS ----------

@app.post("/webhook")
async def webhook(request: Request):
    start = time.time()
    body = await request.body()
    signature = request.headers.get("X-Signature")

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if signature != expected:
        inc_http("/webhook", 401)
        inc_webhook("invalid_signature")
        log(request, 401, start, {"result": "invalid_signature"})
        raise HTTPException(status_code=401, detail="invalid signature")

    data = await request.json()
    msg = WebhookMessage(**data)

    db = get_db()
    try:
        db.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
            (
                msg.message_id,
                msg.from_,
                msg.to,
                msg.ts,
                msg.text,
                datetime.utcnow().isoformat() + "Z"
            )
        )
        db.commit()
        result = "created"
        dup = False
    except sqlite3.IntegrityError:
        result = "duplicate"
        dup = True
    finally:
        db.close()

    inc_http("/webhook", 200)
    inc_webhook(result)
    log(request, 200, start, {
        "message_id": msg.message_id,
        "dup": dup,
        "result": result
    })
    return {"status": "ok"}

@app.get("/messages")
def get_messages(limit: int = 50, offset: int = 0,
                 from_: Optional[str] = None,
                 since: Optional[str] = None,
                 q: Optional[str] = None):
    db = get_db()
    filters = []
    params = []

    if from_:
        filters.append("from_msisdn = ?")
        params.append(from_)
    if since:
        filters.append("ts >= ?")
        params.append(since)
    if q:
        filters.append("LOWER(text) LIKE ?")
        params.append(f"%{q.lower()}%")

    where = "WHERE " + " AND ".join(filters) if filters else ""
    total = db.execute(
        f"SELECT COUNT(*) FROM messages {where}", params
    ).fetchone()[0]

    rows = db.execute(
        f"""
        SELECT * FROM messages
        {where}
        ORDER BY ts ASC, message_id ASC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset]
    ).fetchall()

    db.close()

    return {
        "data": [
            {
                "message_id": r["message_id"],
                "from": r["from_msisdn"],
                "to": r["to_msisdn"],
                "ts": r["ts"],
                "text": r["text"]
            } for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/stats")
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    senders = db.execute("""
        SELECT from_msisdn as sender, COUNT(*) as count
        FROM messages
        GROUP BY from_msisdn
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    first = db.execute("SELECT MIN(ts) FROM messages").fetchone()[0]
    last = db.execute("SELECT MAX(ts) FROM messages").fetchone()[0]

    db.close()

    return {
        "total_messages": total,
        "senders_count": len(senders),
        "messages_per_sender": [
            {"from": s["sender"], "count": s["count"]} for s in senders
        ],
        "first_message_ts": first,
        "last_message_ts": last
    }

@app.get("/health/live")
def live():
    return {"status": "alive"}

@app.get("/health/ready")
def ready():
    return {"status": "ready"}

@app.get("/metrics")
def metrics():
    lines = []
    for (path, status), v in HTTP_METRICS.items():
        lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {v}')
    for result, v in WEBHOOK_METRICS.items():
        lines.append(f'webhook_requests_total{{result="{result}"}} {v}')
    return "\n".join(lines)