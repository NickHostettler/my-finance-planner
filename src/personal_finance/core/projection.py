"""Compound-interest balance projections."""

from typing import List


def project_balance(
    annual_contribution: float,
    years: int,
    annual_return: float,
    initial_balance: float = 0,
    inflation_rate: float = 0,
) -> List[float]:
    values = [initial_balance]
    balance = initial_balance
    for year in range(1, years + 1):
        balance = (balance + annual_contribution) * (1 + annual_return)
        values.append(balance / ((1 + inflation_rate) ** year))
    return values
