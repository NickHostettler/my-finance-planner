"""Life phases and family in the dashboard (#33): the inputs as phases and the result tab."""

import math
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from personal_finance.core.life_phases import LifePhase
from personal_finance.storage import browser_store

ROWS = range(1, browser_store.LIFE_PHASE_ROWS + 1)


def used_rows(workloads: Sequence[Any]) -> int:
    """How many phase rows are used: the leading rows with a workload."""
    count = 0
    for workload in workloads:
        if workload is None or workload == "":
            break
        count += 1
    return count


def _whole(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and float(value).is_integer()
    )


def row_titles(current_age: Any, to_ages: Sequence[Any], visible: int) -> List[str]:
    """Titles like "Phase 2 · ab 34"; the last visible phase lasts until retirement."""
    titles = []
    start: Optional[int] = int(current_age) if _whole(current_age) else None
    for row, to_age in enumerate(to_ages, start=1):
        title = f"Phase {row}" + ("" if start is None else f" · ab {start}")
        if row == visible:
            title += " bis zur Pensionierung"
        titles.append(title)
        start = int(to_age) + 1 if _whole(to_age) else None
    return titles


def phases_from_values(values: Mapping[str, Any], current_age: int, retirement_age: int):
    """The life phases from the stored inputs (``browser_store`` field names).

    The first phase starts today, each next one the year after the previous «bis Alter», the
    last one lasts until retirement. Workloads in percent become decimals. Incomes are monthly
    on the basis of the income input. Raises ``ValueError`` with a German message.
    """
    rows = [
        {part: values.get(f"life_{row}_{part}") for part in browser_store.LIFE_ROW_PARTS}
        for row in ROWS
    ]
    count = used_rows([row["workload"] for row in rows])
    if count == 0:
        raise ValueError("Bitte lege mindestens eine Lebensphase an oder wähle eine Vorlage.")
    phases = []
    start = current_age
    for number, row in enumerate(rows[:count], start=1):
        last = number == count
        if last:
            to_age = retirement_age - 1
        else:
            to_age = row["to"]
            if to_age is None:
                raise ValueError(
                    f"Phase {number}: Bitte gib an, bis zu welchem Alter die Phase dauert."
                )
            if to_age < start:
                raise ValueError(
                    f"Phase {number}: Das Alter «bis» ({to_age}) muss mindestens {start} sein."
                )
            if to_age >= retirement_age - 1:
                raise ValueError(
                    f"Phase {number}: Das Alter «bis» ({to_age}) muss vor der letzten Phase "
                    f"enden, also spätestens bei {retirement_age - 2}."
                )
        workload = row["workload"]
        phases.append(
            LifePhase(
                start,
                max(start, to_age),
                workload / 100 if isinstance(workload, (int, float)) else workload,
                row["income"],
                child_costs=row["costs"],
            )
        )
        if not last:
            start = to_age + 1
    return phases


def child_birth_ages(values: Mapping[str, Any]) -> Tuple[int, ...]:
    """The parent's ages at the births from the filled-in child fields."""
    return tuple(
        values[f"life_child_{child}"]
        for child in range(1, browser_store.LIFE_CHILDREN + 1)
        if values.get(f"life_child_{child}") is not None
    )
