"""Allow ``python -m personal_finance`` to start the dashboard."""

from personal_finance.dashboard import run_dashboard

if __name__ == "__main__":
    run_dashboard(debug=True)
