"""Per-user scenario storage that lives in the user's browser (``localStorage``).

The server never persists user data. Every function here is pure: it receives the
current browser-side state, returns a *new* state, and keeps nothing between calls.
The dashboard stores the returned state in a ``dcc.Store(storage_type="local")``, so
each browser (and therefore each user) only ever sees its own data.

Data coming back from the browser is untrusted (it can be stale, corrupted or edited
by hand), so it is always sanitized before use.

The dashboard works with one flat dict (``SCENARIO_FIELDS``: person A without a prefix,
person B with ``b_``, the household fields). The browser keeps the values by household and
person (:func:`to_stored`); :func:`from_stored` reads every older version.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from personal_finance import config
from personal_finance.core.income import normalize_income

# Version 2 (v1.3): values stored by household and person. Version 1 (v1.0–v1.2): one flat
# dict of one person.
STORAGE_VERSION = 2
MAX_SCENARIO_NAME_LENGTH = 80
MAX_SCENARIOS = 50
MAX_TEXT_LENGTH = 20

# Life phases and family (v1.2): rows of phases and children in the inputs.
LIFE_PHASE_ROWS = 5
LIFE_CHILDREN = 4
LIFE_ROW_PARTS = {"to": "integer", "workload": "number", "income": "number", "costs": "number"}

# The fields of one person (v1.3): person A uses these names, person B the same with the
# prefix "b_". Everything else in SCENARIO_FIELDS belongs to the household.
PERSON_FIELDS: Dict[str, str] = {
    "income": "number",
    "income_period": "text",
    "income_type": "text",
    "canton": "text",
    "current_age": "integer",
    "retirement_age": "integer",
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
    "ahv_average_income": "number",
    "ahv_contribution_years": "integer",
    # Money for a home purchase, in CHF at the time of the purchase (v1.1).
    "home_savings": "number",
    "home_pillar3a": "number",
    "home_pillar2": "number",
    # Salary growth per year in percent (v1.2).
    "salary_growth": "number",
    # Life phases (v1.2). Each phase row: until age (the last one runs until retirement),
    # workload in percent, income per month on the basis of the income input and child costs
    # per month. A row is used while its workload is filled in.
    "life_plan": "text",
    "life_coordination": "text",
    **{
        f"life_{row}_{part}": kind
        for row in range(1, LIFE_PHASE_ROWS + 1)
        for part, kind in LIFE_ROW_PARTS.items()
    },
    "life_role": "text",
    "life_credit_share": "text",
}
PERSON_B_PREFIX = "b_"
PERSON_KEYS = ("a", "b")  # keys of the persons in the stored values


def person_field(field: str, person: str = "a") -> str:
    """The name of a person's field: "income" -> "income" (A) or "b_income" (B)."""
    return field if person == "a" else PERSON_B_PREFIX + field


# Field name -> expected type. Order matches the dashboard inputs.
SCENARIO_FIELDS: Dict[str, str] = {
    "income": "number",
    "income_period": "text",
    "income_type": "text",
    "canton": "text",
    "current_age": "integer",
    "retirement_age": "integer",
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
    # Home ownership (v1.1). Amounts in CHF at the time of the purchase, rates in percent.
    "home_plan": "text",
    "home_price": "number",
    "home_purchase_age": "integer",
    "home_savings": "number",
    "home_pillar3a": "number",
    "home_pillar2": "number",
    "home_gross_income": "number",
    "home_imputed_rate": "number",
    "home_mortgage_rate": "number",
    "home_amortisation": "text",
    "salary_growth": "number",
    # Life phases and family (v1.2). Children: the age of person A at each birth.
    "life_plan": "text",
    "life_coordination": "text",
    **{
        f"life_{row}_{part}": kind
        for row in range(1, LIFE_PHASE_ROWS + 1)
        for part, kind in LIFE_ROW_PARTS.items()
    },
    **{f"life_child_{child}": "integer" for child in range(1, LIFE_CHILDREN + 1)},
    "life_role": "text",
    "life_credit_share": "text",
    "life_child_allowance": "number",
    "life_education_allowance": "number",
    # Household (v1.3): one or two persons, how they live together and, if unmarried, how
    # they share the AHV education credits. Then every field of person B.
    "household": "text",
    "household_relationship": "text",
    "household_credits": "text",
    **{person_field(field, "b"): kind for field, kind in PERSON_FIELDS.items()},
}
LIFE_FIELDS = [field for field in SCENARIO_FIELDS if field.startswith("life_")]
HOUSEHOLD_FIELDS = [
    field
    for field in SCENARIO_FIELDS
    if field not in PERSON_FIELDS and not field.startswith(PERSON_B_PREFIX)
]

# The start values of a person in the inputs (and person B's defaults).
PERSON_DEFAULTS: Dict[str, Any] = {
    "income": 5000,
    "income_period": "monthly",
    "income_type": "net",
    "canton": "ZH",
    "current_age": 35,
    "retirement_age": 65,
    "pillar3a_amount": 350,
    "pillar3b_amount": 500,
    "initial_3a": 0,
    "initial_3b": 0,
    "initial_2": 0,
    "pillar2_mode": "minimum",
    "assumed_return": 0.04,
    "ahv_average_income": 100000,
    "ahv_contribution_years": 44,
    "home_savings": 200_000,
    "home_pillar3a": 0,
    "home_pillar2": 0,
    "salary_growth": config.SALARY_GROWTH_DEFAULT * 100,
    "life_plan": "off",
    "life_coordination": "fixed",
    "life_role": "mother",
    "life_credit_share": "full",
}
# Person B starts without savings for a purchase and as the other parent.
PERSON_B_DEFAULTS: Dict[str, Any] = {**PERSON_DEFAULTS, "home_savings": 0, "life_role": "other"}

# Defaults for fields added after the first release. Older scenarios and remembered inputs
# do not contain them; they are filled in here, so that those scenarios still load.
# Fields without a default (e.g. home_purchase_age: empty = buy now) stay empty.
FIELD_DEFAULTS: Dict[str, Any] = {
    "display_basis": "nominal",
    "ahv_contribution_years": 44,
    "home_plan": "off",
    "home_price": 900_000,
    "home_savings": 200_000,
    "home_pillar3a": 0,
    "home_pillar2": 0,
    "home_imputed_rate": 5.0,
    "home_mortgage_rate": 2.0,
    "home_amortisation": "direct",
    "salary_growth": config.SALARY_GROWTH_DEFAULT * 100,
    # Life phases: the rows and children have no default (empty = not used).
    "life_plan": "off",
    "life_coordination": "fixed",
    "life_role": "mother",
    "life_credit_share": "full",
    "life_child_allowance": config.CHILD_ALLOWANCE_MONTHLY,
    "life_education_allowance": config.EDUCATION_ALLOWANCE_MONTHLY,
    # Household (v1.3): older scenarios are plans of one person (person A).
    "household": "off",
    "household_relationship": "married",
    "household_credits": "half",
    **{person_field(field, "b"): value for field, value in PERSON_B_DEFAULTS.items()},
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


def _amount_from_savings_rate(source: Mapping[str, Any]) -> Optional[float]:
    """The monthly 3a amount of an entry saved with a savings rate (until v1.1).

    Since v1.2 the 3a contribution is always a fixed amount. Entries that used the savings
    rate get the amount that rate gave them: the share of the monthly net income, capped at
    the 3a maximum. ``None`` if the entry did not use the rate or lacks what it takes.
    """
    rate = _clean_value("number", source.get("savings_rate"))
    age = _clean_value("integer", source.get("current_age"))
    if source.get("savings_mode") != "rate" or rate is None or age is None:
        return None
    try:
        monthly_net, _ = normalize_income(
            _clean_value("number", source.get("income")),
            _clean_value("text", source.get("income_period")),
            _clean_value("text", source.get("income_type")),
            age,
            _clean_value("text", source.get("canton")),
        )
    except ValueError:
        return None
    amount = min(max(monthly_net * rate / 100, 0.0), config.PILLAR3A_MONTHLY_MAX)
    return math.floor(amount * 100) / 100


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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _version(value: Any) -> int:
    """The storage version of browser data; missing or invalid counts as the first one."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return 1
    return value


def to_stored(values: Mapping[str, Any]) -> Dict[str, Any]:
    """The values (names of SCENARIO_FIELDS) in the stored layout of the current version.

    ``{"household": {...}, "persons": {"a": {...}, "b": {...}}}``: both persons with the
    same keys (PERSON_FIELDS), so that the data says whose it is.
    """
    clean = sanitize_values(values)
    return {
        "household": {field: clean[field] for field in HOUSEHOLD_FIELDS},
        "persons": {
            person: {field: clean[person_field(field, person)] for field in PERSON_FIELDS}
            for person in PERSON_KEYS
        },
    }


def from_stored(stored: Any, version: Any = STORAGE_VERSION) -> Dict[str, Any]:
    """The sanitized values (SCENARIO_FIELDS) from stored values of any ``version``.

    All migrations happen here, in order:

    * Version 1 (v1.0–v1.2): one flat dict of one person. It becomes person A, the household
      stays off and person B gets the start values. Entries saved with a savings rate (until
      v1.1) get the fixed monthly 3a amount that rate gave them.
    """
    source = _mapping(stored)
    if _version(version) < 2:
        flat = {field: source.get(field) for field in [*PERSON_FIELDS, *HOUSEHOLD_FIELDS]}
        migrated_amount = _amount_from_savings_rate(source)
        if migrated_amount is not None:
            flat["pillar3a_amount"] = migrated_amount
        return sanitize_values(flat)
    household = _mapping(source.get("household"))
    persons = _mapping(source.get("persons"))
    flat = {field: household.get(field) for field in HOUSEHOLD_FIELDS}
    for person in PERSON_KEYS:
        values = _mapping(persons.get(person))
        flat.update({person_field(field, person): values.get(field) for field in PERSON_FIELDS})
    return sanitize_values(flat)


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
    """Return a clean copy of the browser's scenario state in the current version.

    Entries of an older version are migrated (:func:`from_stored`). Never the same object.
    """
    result = empty_scenarios()
    if not isinstance(data, Mapping) or not isinstance(data.get("scenarios"), Mapping):
        return result
    version = data.get("version")
    for raw_name, entry in data["scenarios"].items():
        try:
            name = validate_name(raw_name)
        except ValueError:
            continue
        if not isinstance(entry, Mapping):
            continue
        updated_at = entry.get("updated_at")
        result["scenarios"][name] = {
            "values": to_stored(from_stored(entry.get("values"), version)),
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
        "values": to_stored(values),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return state


def load_scenario(data: Any, name: Any) -> Dict[str, Any]:
    """Return the stored values for ``name`` (a new dict)."""
    normalized = validate_name(name)
    scenarios = sanitize_scenarios(data)["scenarios"]
    if normalized not in scenarios:
        raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
    return from_stored(scenarios[normalized]["values"])


def delete_scenario(data: Any, name: Any) -> Dict[str, Any]:
    """Return a new state without ``name``; raise if it does not exist."""
    normalized = validate_name(name)
    state = sanitize_scenarios(data)
    if state["scenarios"].pop(normalized, None) is None:
        raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
    return state


# --- last inputs ----------------------------------------------------------------


def make_last_inputs(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {"version": STORAGE_VERSION, "values": to_stored(values)}


def read_last_inputs(data: Any) -> Optional[Dict[str, Any]]:
    """Return the remembered values, or ``None`` if nothing usable is stored."""
    if not isinstance(data, Mapping) or not isinstance(data.get("values"), Mapping):
        return None
    return from_stored(data["values"], data.get("version"))
