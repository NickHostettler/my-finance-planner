"""Local SQLite storage for named dashboard scenarios."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


APPLICATION_VERSION = "1"
MAX_SCENARIO_NAME_LENGTH = 80

SCENARIO_FIELDS = {
    "income": "REAL",
    "income_period": "TEXT",
    "income_type": "TEXT",
    "canton": "TEXT",
    "current_age": "INTEGER",
    "retirement_age": "INTEGER",
    "savings_mode": "TEXT",
    "savings_rate": "REAL",
    "pillar3a_amount": "REAL",
    "pillar3b_amount": "REAL",
    "initial_3a": "REAL",
    "initial_3b": "REAL",
    "initial_2": "REAL",
    "pillar2_mode": "TEXT",
    "pillar2_employee": "REAL",
    "pillar2_employer": "REAL",
    "pillar2_return": "REAL",
    "assumed_return": "REAL",
    "display_basis": "TEXT",
    "ahv_average_income": "REAL",
    "ahv_contribution_years": "INTEGER",
}


def default_database_path() -> Path:
    """Return a per-user data location, outside the project checkout."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "SwissFinanceDashboard" / "scenarios.sqlite3"


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Bitte gib einen gültigen Szenarionamen ein.")
    normalized = name.strip()
    if not normalized:
        raise ValueError("Bitte gib einen Namen für das Szenario ein.")
    if len(normalized) > MAX_SCENARIO_NAME_LENGTH:
        raise ValueError(
            f"Der Szenarioname darf höchstens {MAX_SCENARIO_NAME_LENGTH} Zeichen lang sein."
        )
    return normalized


def _connect(database_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path is not None else default_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    columns = ", ".join(f'"{name}" {kind}' for name, kind in SCENARIO_FIELDS.items())
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            application_version TEXT NOT NULL,
            {columns}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS last_inputs (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            {columns}
        )
        """
    )
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(scenarios)")
    }
    migration_defaults = {
        "display_basis": "TEXT NOT NULL DEFAULT 'nominal'",
        "ahv_average_income": "REAL",
        "ahv_contribution_years": "INTEGER NOT NULL DEFAULT 44",
    }
    for column, definition in migration_defaults.items():
        if column not in existing_columns:
            connection.execute(
                f'ALTER TABLE scenarios ADD COLUMN "{column}" {definition}'
            )
    existing_last_input_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(last_inputs)")
    }
    for column, definition in SCENARIO_FIELDS.items():
        if column not in existing_last_input_columns:
            connection.execute(
                f'ALTER TABLE last_inputs ADD COLUMN "{column}" {definition}'
            )
    return connection


def save_last_inputs(values: Dict, database_path: Optional[Path] = None) -> None:
    """Persist the most recently used dashboard inputs for the next launch."""
    missing = set(SCENARIO_FIELDS) - values.keys()
    if missing:
        raise ValueError(f"Für das Speichern fehlen Eingaben: {', '.join(sorted(missing))}.")

    field_names = list(SCENARIO_FIELDS)
    quoted_columns = ", ".join(f'"{field}"' for field in field_names)
    placeholders = ", ".join("?" for _ in field_names)
    updates = ", ".join(f'"{field}" = excluded."{field}"' for field in field_names)
    with closing(_connect(database_path)) as connection, connection:
        connection.execute(
            f"""
            INSERT INTO last_inputs (id, {quoted_columns})
            VALUES (1, {placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
            """,
            [values[field] for field in field_names],
        )


def load_last_inputs(database_path: Optional[Path] = None) -> Optional[Dict]:
    """Load the last dashboard input snapshot, if one has been saved."""
    columns = ", ".join(f'"{field}"' for field in SCENARIO_FIELDS)
    with closing(_connect(database_path)) as connection:
        row = connection.execute(
            f"SELECT {columns} FROM last_inputs WHERE id = 1"
        ).fetchone()
    return dict(row) if row is not None else None


def save_scenario(name: str, values: Dict, database_path: Optional[Path] = None) -> str:
    """Insert or replace a named scenario and return its normalized name."""
    normalized_name = _validate_name(name)
    missing = set(SCENARIO_FIELDS) - values.keys()
    if missing:
        raise ValueError(f"Für das Speichern fehlen Eingaben: {', '.join(sorted(missing))}.")

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    field_names = list(SCENARIO_FIELDS)
    columns = ["name", "created_at", "updated_at", "application_version", *field_names]
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        [f'"{field}" = excluded."{field}"' for field in field_names]
        + [
            "updated_at = excluded.updated_at",
            "application_version = excluded.application_version",
        ]
    )
    parameters = [
        normalized_name,
        timestamp,
        timestamp,
        APPLICATION_VERSION,
        *(values[field] for field in field_names),
    ]

    with closing(_connect(database_path)) as connection, connection:
        connection.execute(
            f"""
            INSERT INTO scenarios ({quoted_columns})
            VALUES ({placeholders})
            ON CONFLICT(name) DO UPDATE SET {updates}
            """,
            parameters,
        )
    return normalized_name


def list_scenarios(database_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Return scenario names and their last saved timestamps."""
    with closing(_connect(database_path)) as connection:
        rows = connection.execute(
            "SELECT name, updated_at FROM scenarios ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [{"name": row["name"], "updated_at": row["updated_at"]} for row in rows]


def load_scenario(name: str, database_path: Optional[Path] = None) -> Dict:
    """Load a saved input snapshot by its exact scenario name."""
    normalized_name = _validate_name(name)
    columns = ", ".join(f'"{field}"' for field in SCENARIO_FIELDS)
    with closing(_connect(database_path)) as connection:
        row = connection.execute(
            f"SELECT {columns} FROM scenarios WHERE name = ?",
            (normalized_name,),
        ).fetchone()
    if row is None:
        raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
    return dict(row)


def delete_scenario(name: str, database_path: Optional[Path] = None) -> bool:
    """Delete one scenario; return whether a row was removed."""
    normalized_name = _validate_name(name)
    with closing(_connect(database_path)) as connection, connection:
        cursor = connection.execute("DELETE FROM scenarios WHERE name = ?", (normalized_name,))
    return cursor.rowcount > 0
