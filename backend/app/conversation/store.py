"""对话状态存储（SQLite）"""
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List


class ConversationStore:
    """SQLite 对话状态存储，支持多轮对话"""

    def __init__(self, db_path: str = "data/conversations.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'initialized',
                    city TEXT,
                    days INTEGER,
                    attractions TEXT,
                    hotel_area TEXT,
                    budget_per_night INTEGER,
                    transport_mode TEXT,
                    search_results TEXT,
                    route_plan TEXT,
                    confirmed_pois TEXT,
                    last_message TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            conn.commit()

    def create(self) -> dict:
        cid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
                (cid, now, now)
            )
            conn.commit()
        return {"id": cid, "created_at": now}

    def get(self, cid: str) -> Optional[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (cid,)
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def update(self, cid: str, **fields):
        fields["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [cid]
        with self._conn() as conn:
            conn.execute(f"UPDATE conversations SET {sets} WHERE id = ?", vals)
            conn.commit()

    def get_state(self, cid: str) -> dict:
        row = self.get(cid)
        if not row:
            return {}
        return {
            "city": row.get("city"),
            "days": row.get("days"),
            "attractions": json.loads(row["attractions"]) if row.get("attractions") else [],
            "hotel_area": row.get("hotel_area"),
            "budget_per_night": row.get("budget_per_night"),
            "transport_mode": row.get("transport_mode") or "mixed",
            "confirmed_pois": json.loads(row["confirmed_pois"]) if row.get("confirmed_pois") else [],
            "state": row.get("state"),
        }

    def add_message(self, cid: str, role: str, content: str):
        mid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (mid, cid, role, content, now)
            )
            conn.execute(
                "UPDATE conversations SET last_message = ?, updated_at = ? WHERE id = ?",
                (content[:200], now, cid)
            )
            conn.commit()

    def get_messages(self, cid: str) -> List[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (cid,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation_summary(self, cid: str) -> str:
        """获取对话历史摘要（用于 Agent 上下文）"""
        msgs = self.get_messages(cid)
        lines = []
        for m in msgs[-6:]:  # 最近6条
            role = "用户" if m["role"] == "user" else "助手"
            lines.append(f"{role}: {m['content'][:100]}")
        return "\n".join(lines)


store = ConversationStore()
