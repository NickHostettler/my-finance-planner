"""
Swiss Personal Finance Planning Tool

Ein Paket für private Finanzplanung nach dem Schweizer Rentensystem.
"""

from importlib.metadata import PackageNotFoundError, version

# Single source of truth for the version is pyproject.toml.
try:
    __version__ = version("swiss-personal-finance")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0+unknown"

__author__ = "Finance Tools"

from personal_finance.calculator import FinanceCalculator  # noqa: E402

__all__ = ["FinanceCalculator", "__version__"]
