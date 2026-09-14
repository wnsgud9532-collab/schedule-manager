import sqlite3
import os
import sys
from datetime import date, time, datetime
from typing import List, Optional, Tuple
from app.models.schedule import Employee, Shift
from app.core import cloud_backup

def _get_app_root() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DB_PATH = os.path.join(_get_app_root(), "data", "schedule.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                shift_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL,
                minutes_before INTEGER NOT NULL DEFAULT 10,
                enabled INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (shift_id) REFERENCES shifts(id)
            );
        """)
        # 기존 DB에 원본 컬럼 없으면 추가 (마이그레이션)
        for col in ("original_start_time", "original_end_time"):
            try:
                conn.execute(f"ALTER TABLE shifts ADD COLUMN {col} TEXT")
            except Exception:
                pass
    restore_from_cloud_if_empty()


def export_snapshot() -> dict:
    """전체 DB 내용을 dict로 직렬화 (구글 시트 백업용)."""
    with get_connection() as conn:
        employees = [dict(r) for r in conn.execute("SELECT * FROM employees")]
        shifts = [dict(r) for r in conn.execute("SELECT * FROM shifts")]
        settings = [dict(r) for r in conn.execute("SELECT * FROM settings")]
    return {"employees": employees, "shifts": shifts, "settings": settings}


def import_snapshot(data: dict):
    """백업 dict로 로컬 DB를 덮어씀."""
    with get_connection() as conn:
        conn.execute("DELETE FROM shifts")
        conn.execute("DELETE FROM employees")
        conn.execute("DELETE FROM settings")
        for e in data.get("employees", []):
            conn.execute("INSERT INTO employees (id, name) VALUES (?, ?)", (e["id"], e["name"]))
        for s in data.get("shifts", []):
            conn.execute(
                "INSERT INTO shifts (id, employee_id, shift_date, start_time, end_time, note, "
                "original_start_time, original_end_time) VALUES (?,?,?,?,?,?,?,?)",
                (s["id"], s["employee_id"], s["shift_date"], s["start_time"], s["end_time"],
                 s.get("note", ""), s.get("original_start_time"), s.get("original_end_time")),
            )
        for row in data.get("settings", []):
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (row["key"], row["value"]))


def _backup_to_cloud():
    """DB 변경 후 구글 시트로 자동 백업. 네트워크/권한 오류는 조용히 무시(앱 동작에 영향 없음)."""
    try:
        cloud_backup.save_backup(export_snapshot())
    except Exception:
        pass


def restore_from_cloud_if_empty():
    """로컬 DB가 비어있으면(앱 재시작 등으로 초기화된 경우) 구글 시트 백업에서 자동 복원."""
    with get_connection() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM shifts").fetchone()["n"]
    if n > 0:
        return
    try:
        data = cloud_backup.load_backup()
        if data and data.get("shifts"):
            import_snapshot(data)
    except Exception:
        pass


def _upsert_employee_conn(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM employees WHERE name = ?", (name,)).fetchone()
    return row["id"]


def upsert_employee(name: str) -> int:
    with get_connection() as conn:
        return _upsert_employee_conn(conn, name)


def insert_shifts_bulk(shifts: List[Shift]):
    with get_connection() as conn:
        for shift in shifts:
            emp_id = _upsert_employee_conn(conn, shift.employee_name)
            conn.execute(
                "INSERT INTO shifts (employee_id, shift_date, start_time, end_time, note) VALUES (?,?,?,?,?)",
                (emp_id, shift.date.isoformat(), shift.start_time.strftime("%H:%M"),
                 shift.end_time.strftime("%H:%M"), shift.note)
            )
    _backup_to_cloud()


def delete_shifts_for_month(year: int, month: int):
    prefix = f"{year}-{month:02d}"
    with get_connection() as conn:
        conn.execute("DELETE FROM shifts WHERE shift_date LIKE ?", (f"{prefix}%",))
    _backup_to_cloud()


def get_shifts_for_date(target_date: date) -> List[Shift]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, s.employee_id, e.name, s.shift_date, s.start_time, s.end_time, s.note
            FROM shifts s JOIN employees e ON s.employee_id = e.id
            WHERE s.shift_date = ? AND s.note != '삭제'
            ORDER BY s.start_time
        """, (target_date.isoformat(),)).fetchall()
    return [_row_to_shift(r) for r in rows]


def get_shifts_for_month(year: int, month: int) -> List[Shift]:
    prefix = f"{year}-{month:02d}"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, s.employee_id, e.name, s.shift_date, s.start_time, s.end_time, s.note
            FROM shifts s JOIN employees e ON s.employee_id = e.id
            WHERE s.shift_date LIKE ? AND s.note != '삭제'
            ORDER BY s.shift_date, s.start_time
        """, (f"{prefix}%",)).fetchall()
    return [_row_to_shift(r) for r in rows]


def get_shifts_for_employee_date(employee_name: str, target_date: date) -> List[Shift]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, s.employee_id, e.name, s.shift_date, s.start_time, s.end_time, s.note
            FROM shifts s JOIN employees e ON s.employee_id = e.id
            WHERE e.name = ? AND s.shift_date = ? AND s.note != '삭제'
            ORDER BY s.start_time
        """, (employee_name, target_date.isoformat())).fetchall()
    return [_row_to_shift(r) for r in rows]


def get_all_employees() -> List[Employee]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT e.id, e.name FROM employees e
            JOIN shifts s ON e.id = s.employee_id
            ORDER BY e.name
        """).fetchall()
    return [Employee(id=r["id"], name=r["name"]) for r in rows]


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    _backup_to_cloud()


def update_shift(shift_id: int, start_time: time, end_time: time, note: str):
    with get_connection() as conn:
        # 최초 편집 시 원본 값 자동 보존
        row = conn.execute(
            "SELECT start_time, end_time, original_start_time FROM shifts WHERE id=?",
            (shift_id,),
        ).fetchone()
        if row and row["original_start_time"] is None:
            conn.execute(
                "UPDATE shifts SET original_start_time=?, original_end_time=? WHERE id=?",
                (row["start_time"], row["end_time"], shift_id),
            )
        conn.execute(
            "UPDATE shifts SET start_time=?, end_time=?, note=? WHERE id=?",
            (start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), note, shift_id),
        )
    _backup_to_cloud()


def restore_shift_original(shift_id: int) -> bool:
    """원본 시간으로 복구. 원본이 없으면 False 반환."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT original_start_time, original_end_time FROM shifts WHERE id=?",
            (shift_id,),
        ).fetchone()
        restored = bool(row and row["original_start_time"])
        if restored:
            conn.execute(
                "UPDATE shifts SET start_time=?, end_time=?, note='', "
                "original_start_time=NULL, original_end_time=NULL WHERE id=?",
                (row["original_start_time"], row["original_end_time"], shift_id),
            )
    if restored:
        _backup_to_cloud()
    return restored


def has_original(shift_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT original_start_time FROM shifts WHERE id=?", (shift_id,)
        ).fetchone()
        return bool(row and row["original_start_time"])


def count_modified_shifts() -> int:
    """편집된(원본이 보존된) 근무 수 반환."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM shifts WHERE original_start_time IS NOT NULL"
        ).fetchone()
        return row["cnt"] if row else 0


def restore_all_originals() -> int:
    """편집된 모든 근무를 원본으로 복구. 복구된 건수 반환."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE shifts
            SET start_time = original_start_time,
                end_time   = original_end_time,
                note       = '',
                original_start_time = NULL,
                original_end_time   = NULL
            WHERE original_start_time IS NOT NULL
        """)
        n = conn.execute("SELECT changes() as n").fetchone()["n"]
    if n:
        _backup_to_cloud()
    return n


def get_modified_shifts() -> List[dict]:
    """수정되었거나 휴무 처리된(원본이 보존된) 근무 전체 반환 (수정 기록)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, e.name AS employee_name, s.shift_date, s.start_time, s.end_time, s.note,
                   s.original_start_time, s.original_end_time
            FROM shifts s JOIN employees e ON s.employee_id = e.id
            WHERE s.original_start_time IS NOT NULL
            ORDER BY s.shift_date DESC, e.name
        """).fetchall()
    return [
        {
            "id": r["id"],
            "employee_name": r["employee_name"],
            "date": date.fromisoformat(r["shift_date"]),
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "note": r["note"] or "",
            "original_start_time": r["original_start_time"],
            "original_end_time": r["original_end_time"],
        }
        for r in rows
    ]


def delete_shift(shift_id: int):
    """소프트 삭제: 원본을 보존하고 note='삭제'로 숨김 → 전체 복구 가능."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT start_time, end_time, original_start_time FROM shifts WHERE id=?",
            (shift_id,),
        ).fetchone()
        if row and row["original_start_time"] is None:
            conn.execute(
                "UPDATE shifts SET original_start_time=?, original_end_time=? WHERE id=?",
                (row["start_time"], row["end_time"], shift_id),
            )
        conn.execute("UPDATE shifts SET note='삭제' WHERE id=?", (shift_id,))
    _backup_to_cloud()


def _row_to_shift(row) -> Shift:
    d = date.fromisoformat(row["shift_date"])
    st = time.fromisoformat(row["start_time"])
    et = time.fromisoformat(row["end_time"])
    return Shift(
        id=row["id"],
        employee_id=row["employee_id"],
        employee_name=row["name"],
        date=d,
        start_time=st,
        end_time=et,
        note=row["note"] or "",
    )
