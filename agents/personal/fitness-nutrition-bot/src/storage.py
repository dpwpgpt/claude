import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    sex TEXT NOT NULL,
    age INTEGER NOT NULL,
    height_cm REAL NOT NULL,
    weight_kg REAL NOT NULL,
    activity_level TEXT NOT NULL,
    goal TEXT NOT NULL,
    target_calories REAL NOT NULL,
    target_protein_g REAL NOT NULL,
    target_fat_g REAL NOT NULL,
    target_carbs_g REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS log_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    log_date TEXT NOT NULL,
    label TEXT NOT NULL,
    calories REAL NOT NULL,
    protein_g REAL NOT NULL,
    fat_g REAL NOT NULL,
    carbs_g REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass
class Profile:
    user_id: int
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    target_calories: float
    target_protein_g: float
    target_fat_g: float
    target_carbs_g: float


@dataclass
class LogEntry:
    label: str
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class Storage:
    def __init__(self, db_path: str):
        self._db_path = db_path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_profile(self, profile: Profile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles (
                    user_id, sex, age, height_cm, weight_kg, activity_level, goal,
                    target_calories, target_protein_g, target_fat_g, target_carbs_g, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    sex=excluded.sex,
                    age=excluded.age,
                    height_cm=excluded.height_cm,
                    weight_kg=excluded.weight_kg,
                    activity_level=excluded.activity_level,
                    goal=excluded.goal,
                    target_calories=excluded.target_calories,
                    target_protein_g=excluded.target_protein_g,
                    target_fat_g=excluded.target_fat_g,
                    target_carbs_g=excluded.target_carbs_g,
                    updated_at=excluded.updated_at
                """,
                (
                    profile.user_id,
                    profile.sex,
                    profile.age,
                    profile.height_cm,
                    profile.weight_kg,
                    profile.activity_level,
                    profile.goal,
                    profile.target_calories,
                    profile.target_protein_g,
                    profile.target_fat_g,
                    profile.target_carbs_g,
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_profile(self, user_id: int) -> Optional[Profile]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT user_id, sex, age, height_cm, weight_kg, activity_level, goal,
                       target_calories, target_protein_g, target_fat_g, target_carbs_g
                FROM profiles WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        return Profile(*row) if row else None

    def add_log_entry(self, user_id: int, entry: LogEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO log_entries (
                    user_id, log_date, label, calories, protein_g, fat_g, carbs_g, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    date.today().isoformat(),
                    entry.label,
                    entry.calories,
                    entry.protein_g,
                    entry.fat_g,
                    entry.carbs_g,
                    datetime.utcnow().isoformat(),
                ),
            )

    def today_entries(self, user_id: int) -> List[LogEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT label, calories, protein_g, fat_g, carbs_g
                FROM log_entries
                WHERE user_id = ? AND log_date = ?
                ORDER BY id
                """,
                (user_id, date.today().isoformat()),
            ).fetchall()
        return [LogEntry(*row) for row in rows]
