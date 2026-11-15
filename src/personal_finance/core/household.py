"""A household of two persons (v1.3, #44): what they share and what living together changes.

Each person keeps an own profile (income, ages, pension pots, life phases) and is computed
like a single plan. The household adds:

* how the two live together (:data:`MARRIED` also stands for a registered partnership),
* how the AHV education credits for the shared children are split,
* the cap on the two AHV pensions of a married couple (:func:`couple_ahv`),
* the children's birth ages from the view of the second person (:func:`shift_birth_ages`).

All functions are pure and raise ``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

from personal_finance.core import ahv

PERSON_A = "Person A"
PERSON_B = "Person B"
LABELS = (PERSON_A, PERSON_B)

MARRIED = "married"  # married or registered partnership: same rules in AHV and BVG
UNMARRIED = "unmarried"
RELATIONSHIPS = (MARRIED, UNMARRIED)

# Education credits of unmarried parents (AHVV Art. 52fbis): by agreement half each or in
# full to one of them. Married couples always share them half each (AHVG Art. 29sexies).
CREDITS_HALF = "half"
CREDITS_A = "a"
CREDITS_B = "b"
CREDIT_SPLITS = (CREDITS_HALF, CREDITS_A, CREDITS_B)


@dataclass(frozen=True)
class Household:
    """What the two persons share apart from a home purchase."""

    relationship: str = MARRIED
    credits: str = CREDITS_HALF  # only used if unmarried

    @property
    def married(self) -> bool:
        return self.relationship == MARRIED

    @property
    def credit_shares(self) -> Tuple[float, float]:
        """Share of the education credits of person A and person B (together 1)."""
        if self.married or self.credits == CREDITS_HALF:
            return 0.5, 0.5
        return (1.0, 0.0) if self.credits == CREDITS_A else (0.0, 1.0)


def validate_household(relationship: Any, credits: Any = CREDITS_HALF) -> Household:
    if relationship not in RELATIONSHIPS:
        raise ValueError("Bitte wähle, ob ihr verheiratet seid oder nicht.")
    if credits not in CREDIT_SPLITS:
        raise ValueError("Bitte wähle, wie ihr die AHV-Erziehungsgutschriften aufteilt.")
    return Household(relationship, credits)


@dataclass(frozen=True)
class CoupleAhv:
    """The AHV pensions of both persons per month in today's CHF, after the cap."""

    person_a: Optional[float]  # None: no AHV estimate for this person
    person_b: Optional[float]
    uncapped_total: Optional[float]  # None unless both are known
    capped: bool

    @property
    def total(self) -> Optional[float]:
        if self.person_a is None or self.person_b is None:
            return None
        return self.person_a + self.person_b


def _pension(value: Any) -> Optional[float]:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Die AHV-Rente muss mindestens 0 CHF betragen.")
    return float(value)


def couple_ahv(monthly_a: Any, monthly_b: Any, married: bool) -> CoupleAhv:
    """Both AHV pensions; a married couple gets at most 150 % of the maximum pension.

    Both pensions are lowered in the same proportion. MODELLANNAHME: the cap is applied in
    today's CHF, as if both retired today; unmarried couples have no cap.
    """
    person_a, person_b = _pension(monthly_a), _pension(monthly_b)
    if person_a is None or person_b is None:
        return CoupleAhv(person_a, person_b, None, False)
    total = person_a + person_b
    cap = ahv.COUPLE_MAXIMUM_MONTHLY_PENSION
    if not married or total <= cap:
        return CoupleAhv(person_a, person_b, total, False)
    factor = cap / total
    return CoupleAhv(person_a * factor, person_b * factor, total, True)


def shift_birth_ages(
    birth_ages: Sequence[Any], age_a: int, age_b: int, label: str = PERSON_B
) -> Tuple[Any, ...]:
    """The children's birth ages entered as ages of person A, seen from person B.

    Values that are not whole numbers are passed on unchanged (the family check explains
    them).
    """
    offset = age_b - age_a
    shifted = []
    for number, value in enumerate(birth_ages, start=1):
        if isinstance(value, bool) or not isinstance(value, int):
            shifted.append(value)
            continue
        age = value + offset
        if age < 0:
            raise ValueError(
                f"Kind {number}: {label} wäre bei der Geburt noch nicht geboren. Bitte prüfe "
                f"das Alter von {PERSON_A} bei der Geburt."
            )
        shifted.append(age)
    return tuple(shifted)
