# scripts/init_db.py
"""初始化任务数据库 data/tasks.db"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tasks.db"


def init_tasks_db():
    """创建任务表"""
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        title         TEXT NOT NULL,
        source_email  TEXT,
        due_date      TEXT,
        status        TEXT DEFAULT '待办',
        created_at    TEXT NOT NULL
    );
    """)

    conn.commit()

    count = cur.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    print(f"数据库已就绪：{DB_PATH}")
    print(f"  tasks: {count} 条")

    conn.close()


if __name__ == "__main__":
    init_tasks_db()