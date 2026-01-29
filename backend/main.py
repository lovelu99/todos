#from fastapi import FastAPI, HTTPException
import os
import logging
import time
import socket
import mysql.connector
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel


app = FastAPI()
# HARD-CODED CONFIG (as requested)


# -------------------------------------------------
# Logging configuration
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("backend")


HOSTNAME = socket.gethostname()

# -------------------------------------------------
# Access log middleware
# -------------------------------------------------
@app.middleware("http")
async def access_log(request: Request, call_next):
    start_time = time.time()

    response: Response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "%s %s %s %s %sms served_by=%s",
        request.client.host if request.client else "-",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        HOSTNAME,
    )

    # Optional: add header so curl/browser can see it
    response.headers["X-Served-By"] = HOSTNAME
    response.headers["X-Response-Time-ms"] = str(duration_ms)

    return response

DB_HOST = os.getenv("DB_HOST", "mysql")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "AppPass123!")
DB_NAME = os.getenv("DB_NAME", "three_tier_app")
DB_PORT = int(os.getenv("DB_PORT", "3306"))


def get_conn():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT,
        )
    except mysql.connector.Error:
        logger.exception("MySQL connection failed")
        raise HTTPException(status_code=503, detail="Database unavailable")

class TodoCreate(BaseModel):
    title: str

class TodoUpdate(BaseModel):
    title: str

class TodoPatch(BaseModel):
    done: bool

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/todos")
def list_todos():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, title, done, created_at FROM todos ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"todos": rows}

@app.post("/api/todos")
def create_todo(body: TodoCreate):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO todos (title, done) VALUES (%s, %s)", (title, False))
    conn.commit()
    todo_id = cur.lastrowid
    cur.close()
    conn.close()

    return {"id": todo_id, "title": title, "done": False}

def ensure_todo_exists(cur, todo_id: int) -> None:
    cur.execute("SELECT id FROM todos WHERE id=%s", (todo_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="todo not found")

@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    ensure_todo_exists(cur, todo_id)

    cur.execute("UPDATE todos SET title=%s WHERE id=%s", (title, todo_id))
    conn.commit()

    cur.execute("SELECT id, title, done, created_at FROM todos WHERE id=%s", (todo_id,))
    updated = cur.fetchone()

    cur.close()
    conn.close()
    return {"todo": updated}

@app.patch("/api/todos/{todo_id}")
def patch_todo(todo_id: int, body: TodoPatch):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    ensure_todo_exists(cur, todo_id)

    # MySQL stores BOOLEAN as TINYINT(1)
    cur.execute("UPDATE todos SET done=%s WHERE id=%s", (1 if body.done else 0, todo_id))
    conn.commit()

    cur.execute("SELECT id, title, done, created_at FROM todos WHERE id=%s", (todo_id,))
    updated = cur.fetchone()

    cur.close()
    conn.close()
    return {"todo": updated}

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    ensure_todo_exists(cur, todo_id)

    cur.execute("DELETE FROM todos WHERE id=%s", (todo_id,))
    conn.commit()

    cur.close()
    conn.close()
    return {"deleted": True, "id": todo_id}
