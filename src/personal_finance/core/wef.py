"""Wohneigentumsförderung (WEF): money from the 2nd pillar and pillar 3a for a home.

* :func:`pillar2_limit`: the highest advance withdrawal (Vorbezug) from the pension fund.
* :func:`pillar3a_limit`: the highest withdrawal from pillar 3a.
* :func:`check_amount`: checks an amount the user wants to use against such a limit.

The rules and their sources are in :mod:`personal_finance.config` (``WEF_*``). Pension
funds may have stricter rules in their regulations. All functions are pure and raise
``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from personal_finance import config


@dataclass(frozen=True)
class WithdrawalLimit:
    """How much can be withdrawn at the time of the purchase (CHF)."""

    balance: float
    maximum: float  # 0 if no withdrawal is possible
    minimum: float  # smallest allowed withdrawal (0 = any amount)
    reasons: Tuple[str, ...]  # why less than the balance (or nothing) is available


def _chf(value: float) -> str:
    return f"CHF {value:,.0f}".replace(",", "’")


def _amount(value, message: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    if not math.isfinite(value) or value < 0:
        raise ValueError(message)
    return float(value)


def _age(value, message: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(message)
    return value


def _too_soon(years_since_last_withdrawal: Optional[int]) -> bool:
    return (
        years_since_last_withdrawal is not None
        and years_since_last_withdrawal < config.WEF_MIN_YEARS_BETWEEN_WITHDRAWALS
    )


_TOO_SOON = f"Ein Bezug ist nur alle {config.WEF_MIN_YEARS_BETWEEN_WITHDRAWALS} Jahre möglich."


def latest_pillar2_age(retirement_age: int) -> int:
    """Last age for an advance withdrawal: 3 years before retirement or the reference age."""
    return min(config.WEF_REFERENCE_AGE, retirement_age) - config.WEF_PILLAR2_DEADLINE_YEARS


def pillar2_limit(
    balance,
    age: int,
    retirement_age: int,
    balance_at_50=None,
    years_since_last_withdrawal: Optional[int] = None,
) -> WithdrawalLimit:
    """Highest advance withdrawal from the pension fund at ``age``.

    Args:
        balance: Pension fund balance (Freizügigkeitsleistung) at the withdrawal.
        age: Age at the withdrawal.
        retirement_age: Planned retirement age.
        balance_at_50: Balance at age 50, if known. Only used from age 50; if unknown, the
            model cautiously uses half of the balance.
        years_since_last_withdrawal: ``None`` if there was no earlier withdrawal.
    """
    balance = _amount(balance, "Das Pensionskassenguthaben muss mindestens 0 CHF betragen.")
    age = _age(age, "Das Alter beim Vorbezug muss eine ganze Zahl sein.")
    retirement_age = _age(retirement_age, "Das Pensionierungsalter muss eine ganze Zahl sein.")
    if balance_at_50 is not None:
        balance_at_50 = _amount(
            balance_at_50, "Das Guthaben im Alter 50 muss mindestens 0 CHF betragen."
        )
    minimum = config.WEF_PILLAR2_MIN_AMOUNT

    def none_possible(reason: str) -> WithdrawalLimit:
        return WithdrawalLimit(balance, 0.0, minimum, (reason,))

    latest = latest_pillar2_age(retirement_age)
    if age > latest:
        return none_possible(
            f"Ein Vorbezug ist nur bis {config.WEF_PILLAR2_DEADLINE_YEARS} Jahre vor der "
            f"Pensionierung möglich, also bis Alter {latest}. Manche Kassen setzen die Frist "
            "früher an: Reglement der eigenen Kasse prüfen."
        )
    if _too_soon(years_since_last_withdrawal):
        return none_possible(_TOO_SOON)

    reasons = []
    maximum = balance
    if age >= config.WEF_PILLAR2_HALF_RULE_AGE:
        half = balance / 2
        if balance_at_50 is None:
            maximum = half
            reasons.append(
                "Ab 50 ist höchstens das Guthaben im Alter 50 oder die Hälfte des aktuellen "
                "Guthabens verfügbar. Das Guthaben mit 50 ist nicht bekannt, deshalb rechnet "
                f"das Modell vorsichtig mit der Hälfte ({_chf(half)}). Den genauen Betrag "
                "nennt dein Pensionskassenausweis."
            )
        else:
            maximum = max(min(balance_at_50, balance), half)
            if maximum < balance:
                reasons.append(
                    "Ab 50 ist höchstens das Guthaben im Alter 50 "
                    f"({_chf(min(balance_at_50, balance))}) oder die Hälfte des aktuellen "
                    f"Guthabens ({_chf(half)}) verfügbar, je nachdem, was höher ist."
                )
    if maximum < minimum:
        return none_possible(
            f"Ein Vorbezug muss mindestens {_chf(minimum)} betragen (ausser für Anteilscheine "
            f"von Wohnbaugenossenschaften). Verfügbar wären nur {_chf(maximum)}."
        )
    return WithdrawalLimit(balance, maximum, minimum, tuple(reasons))


def pillar3a_limit(balance, years_since_last_withdrawal: Optional[int] = None) -> WithdrawalLimit:
    """Highest withdrawal from pillar 3a for an owner-occupied home: the whole balance."""
    balance = _amount(balance, "Das 3a-Guthaben muss mindestens 0 CHF betragen.")
    if _too_soon(years_since_last_withdrawal):
        return WithdrawalLimit(balance, 0.0, 0.0, (_TOO_SOON,))
    return WithdrawalLimit(balance, balance, 0.0, ())


def check_amount(amount, limit: WithdrawalLimit, source: str) -> float:
    """Return ``amount`` if it may be withdrawn, else raise ``ValueError``.

    ``source`` names where the money comes from, e.g. "aus der Pensionskasse".
    """
    amount = _amount(amount, f"Der Betrag {source} muss mindestens 0 CHF betragen.")
    if amount == 0:
        return amount
    explanation = (" " + " ".join(limit.reasons)) if limit.reasons else ""
    if limit.maximum == 0:
        explanation = explanation or (
            f" Das Guthaben beträgt voraussichtlich {_chf(limit.balance)}."
        )
        raise ValueError(f"Ein Bezug {source} ist zum Kaufzeitpunkt nicht möglich.{explanation}")
    if amount < limit.minimum:
        raise ValueError(
            f"Ein Bezug {source} muss mindestens {_chf(limit.minimum)} betragen "
            "(ausser für Anteilscheine von Wohnbaugenossenschaften)."
        )
    if amount > limit.maximum + 0.005:
        raise ValueError(
            f"{source[0].upper()}{source[1:]} sind zum Kaufzeitpunkt höchstens "
            f"{_chf(limit.maximum)} möglich (Guthaben voraussichtlich "
            f"{_chf(limit.balance)}).{explanation}"
        )
    return amount
