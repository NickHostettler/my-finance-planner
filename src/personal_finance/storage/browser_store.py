"""Per-user scenario storage that lives in the user's browser (``localStorage``).

The server never persists user data. Every function here is pure: it receives the
current browser-side state, returns a *new* state, and keeps nothing between calls.
The dashboard stores the returned state in a ``dcc.Store(storage_type="local")``, so
each browser (and therefore each user) only ever sees its own data.

Data coming back from the browser is untrusted (it can be stale, corrupted or edited
by hand), so it is always sanitized before use.
"""

import copy
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

STORAGE_VERSION = 1
MAX_SCENARIO_NAME_LENGTH = 80
MAX_SCENARIOS = 50
MAX_TEXT_LENGTH = 20

# Field name -> expected type. Order matches the dashboard inputs.
SCENARIO_FIELDS: Dict[str, str] = {
    "income": "number",
    "income_period": "text",
    "income_type": "text",
    "canton": "text",
    "current_age": "integer",
    "retirement_age": "integer",
    "savings_mode": "text",
    "savings_rate": "number",
    "pillar3a_amount": "number",
    "pillar3b_amount": "number",
    "initial_3a": "number",
    "initial_3b": "number",
    "initial_2": "number",
    "pillar2_mode": "text",
    "pillar2_employee": "number",
    "pillar2_employer": "number",
    "pillar2_return": "number",
    "assumed_return": "number",
    "display_basis": "text",
    "ahv_average_income": "number",
    "ahv_contribution_years": "integer",
}

# Defaults for fields added after the first release (kept from the former SQLite store).
FIELD_DEFAULTS: Dict[str, Any] = {
    "display_basis": "nominal",
    "ahv_contribution_years": 44,
}


# --- validation -------------------------------------------------------------------


def validate_name(name: Any) -> str:
    """Return the trimmed scenario name or raise ``ValueError`` with a user message."""
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


def _clean_value(kind: str, value: Any) -> Any:
    """Return ``value`` if it matches ``kind``, else ``None``."""
    if value is None or isinstance(value, bool):
        return None
    if kind == "text":
        return value if isinstance(value, str) and len(value) <= MAX_TEXT_LENGTH else None
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if kind == "integer":
        return int(value) if float(value).is_integer() else None
    return value


def sanitize_values(values: Any) -> Dict[str, Any]:
    """Keep only known fields with valid types; fill in defaults for missing ones."""
    source = values if isinstance(values, Mapping) else {}
    cleaned = {}
    for field, kind in SCENARIO_FIELDS.items():
        value = _clean_value(kind, source.get(field))
        if value is None:
            value = FIELD_DEFAULTS.get(field)
        cleaned[field] = value
    return cleaned


def values_from_inputs(input_values: List[Any]) -> Dict[str, Any]:
    """Map the dashboard input values (in ``SCENARIO_FIELDS`` order) to a dict."""
    if len(input_values) != len(SCENARIO_FIELDS):
        raise ValueError("Für das Speichern fehlen Eingaben.")
    return sanitize_values(dict(zip(SCENARIO_FIELDS, input_values)))


def values_to_inputs(values: Mapping[str, Any]) -> List[Any]:
    """Inverse of :func:`values_from_inputs`."""
    return [values[field] for field in SCENARIO_FIELDS]


# --- scenarios ------------------------------------------------------------------


def empty_scenarios() -> Dict[str, Any]:
    return {"version": STORAGE_VERSION, "scenarios": {}}


def sanitize_scenarios(data: Any) -> Dict[str, Any]:
    """Return a clean copy of the browser's scenario state (never the same object)."""
    result = empty_scenarios()
    if not isinstance(data, Mapping) or not isinstance(data.get("scenarios"), Mapping):
        return result
    for raw_name, entry in data["scenarios"].items():
        try:
            name = validate_name(raw_name)
        except ValueError:
            continue
        if not isinstance(entry, Mapping):
            continue
        updated_at = entry.get("updated_at")
        result["scenarios"][name] = {
            "values": sanitize_values(entry.get("values")),
            "updated_at": updated_at if isinstance(updated_at, str) else "",
        }
        if len(result["scenarios"]) >= MAX_SCENARIOS:
            break
    return result


def list_scenarios(data: Any) -> List[Dict[str, str]]:
    """Scenario names (case-insensitively sorted) with their last saved timestamps."""
    scenarios = sanitize_scenarios(data)["scenarios"]
    return [
        {"name": name, "updated_at": scenarios[name]["updated_at"]}
        for name in sorted(scenarios, key=str.casefold)
    ]


def save_scenario(data: Any, name: Any, values: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a new state with ``name`` inserted or replaced."""
    normalized = validate_name(name)
    state = sanitize_scenarios(data)
    if normalized not in state["scenarios"] and len(state["scenarios"]) >= MAX_SCENARIOS:
        raise ValueError(
            f"Es können höchstens {MAX_SCENARIOS} Szenarien gespeichert werden. "
            "Bitte lösche zuerst ein altes Szenario."
        )
    state["scenarios"][normalized] = {
        "values": sanitize_values(values),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return state


def load_scenario(data: Any, name: Any) -> Dict[str, Any]:
    """Return a copy of the stored values for ``name``."""
    normalized = validate_name(name)
    scenarios = sanitize_scenarios(data)["scenarios"]
    if normalized not in scenarios:
        raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
    return copy.deepcopy(scenarios[normalized]["values"])


def delete_scenario(data: Any, name: Any) -> Dict[str, Any]:
    """Return a new state without ``name``; raise if it does not exist."""
    normalized = validate_name(name)
    state = sanitize_scenarios(data)
    if state["scenarios"].pop(normalized, None) is None:
        raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
    return state


# --- last inputs ----------------------------------------------------------------


def make_last_inputs(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {"version": STORAGE_VERSION, "values": sanitize_values(values)}


def read_last_inputs(data: Any) -> Optional[Dict[str, Any]]:
    """Return the remembered values, or ``None`` if nothing usable is stored."""
    if not isinstance(data, Mapping) or not isinstance(data.get("values"), Mapping):
        return None
    return sanitize_values(data["values"])
