"""Compound-interest balance projections."""

from typing import List, Mapping, Optional, Sequence


def project_balance(
    annual_contribution: float,
    years: int,
    annual_return: float,
    initial_balance: float = 0,
    inflation_rate: float = 0,
    withdrawals: Optional[Mapping[int, float]] = None,
) -> List[float]:
    """Balance at the start of each year ``0..years``.

    Contributions are paid at the start of each year and then earn the return.
    ``withdrawals`` maps a year index to an amount taken out at that point (e.g. a
    withdrawal for a home purchase); the balance never drops below 0. Values after year 0
    are divided by the inflation of the years so far (0 = nominal).
    """
    withdrawals = withdrawals or {}
    balance = initial_balance
    if 0 in withdrawals:
        balance = max(0.0, balance - withdrawals[0])
    values = [balance]
    for year in range(1, years + 1):
        balance = (balance + annual_contribution) * (1 + annual_return)
        if year in withdrawals:
            balance = max(0.0, balance - withdrawals[year])
        values.append(balance / ((1 + inflation_rate) ** year))
    return values


def deflate(values: Sequence[float], inflation_rate: float) -> List[float]:
    """Nominal values per year (index 0 = today) in today's purchasing power."""
    return [value / ((1 + inflation_rate) ** year) for year, value in enumerate(values)]
