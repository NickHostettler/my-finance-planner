"""Dash callbacks. Importing this module registers them on the app.

Privacy rule: callbacks are pure request/response functions. User data arrives from the
user's own browser (inputs and ``dcc.Store`` state), is processed, and goes back only to
that browser. Nothing is written to disk, cached, kept in module state, or logged.
"""

import math

from dash import Input, Output, State, ctx, html, no_update

from personal_finance import config
from personal_finance.calculator import FinanceCalculator
from personal_finance.core import ahv
from personal_finance.core.income import normalize_income
from personal_finance.core.pillar_2 import Pillar2Result
from personal_finance.core.projection import project_balance
from personal_finance.dashboard.app import app
from personal_finance.dashboard.components import (
    money,
)
from personal_finance.dashboard.layout import (
    LAST_INPUTS_STORE_ID,
    NOTICE_STORE_ID,
    SCENARIOS_STORE_ID,
    STORAGE_KEY_PREFIX,
)
from personal_finance.dashboard.results import results_view
from personal_finance.storage import browser_store


@app.callback(
    Output("rate-control", "style"),
    Output("amount-control", "style"),
    Input("savings-mode-input", "value"),
)
def update_savings_controls(mode):
    return (
        {"display": "block" if mode == "rate" else "none"},
        {"display": "block" if mode == "amount" else "none"},
    )


SCENARIO_INPUT_IDS = [
    "monthly-income-input",
    "income-period-input",
    "income-type-input",
    "canton-input",
    "current-age-input",
    "retirement-age-input",
    "savings-mode-input",
    "pillar3a-rate-input",
    "pillar3a-amount-input",
    "pillar3b-amount-input",
    "pillar3a-initial-input",
    "pillar3b-initial-input",
    "pillar2-initial-input",
    "pillar2-mode-input",
    "pillar2-employee-input",
    "pillar2-employer-input",
    "pillar2-return-input",
    "return-input",
    "display-basis-input",
    "ahv-average-income-input",
    "ahv-contribution-years-input",
]


def _scenario_options(store_data):
    return [
        {"label": item["name"], "value": item["name"]}
        for item in browser_store.list_scenarios(store_data)
    ]


def _scenario_action_response(
    options,
    selected_name,
    message,
    values=None,
    scenario_name_value=no_update,
    store_data=no_update,
    is_error=False,
):
    status_class = (
        "scenario-status-message scenario-status-error"
        if is_error
        else "scenario-status-message"
    )
    status = html.Span(message, className=status_class) if message else ""
    updated_values = (
        browser_store.values_to_inputs(values)
        if values is not None
        else [no_update] * len(SCENARIO_INPUT_IDS)
    )
    return [options, selected_name, status, scenario_name_value, *updated_values, store_data]


@app.callback(
    Output("scenario-select", "options"),
    Output("scenario-select", "value"),
    Output("scenario-status", "children"),
    Output("scenario-name-input", "value"),
    *[Output(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    Output(SCENARIOS_STORE_ID, "data"),
    Input("scenario-initial-load", "n_intervals"),
    Input("scenario-save-button", "n_clicks"),
    Input("scenario-load-button", "n_clicks"),
    Input("scenario-delete-button", "n_clicks"),
    State("scenario-name-input", "value"),
    State("scenario-select", "value"),
    State(SCENARIOS_STORE_ID, "data"),
    *[State(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
)
def manage_scenarios(
    _initial_load,
    _save_clicks,
    _load_clicks,
    _delete_clicks,
    scenario_name,
    selected_name,
    store_data,
    *input_values,
):
    """Save, load or delete named scenarios in this user's browser storage."""
    try:
        trigger = ctx.triggered_id
        if trigger == "scenario-initial-load":
            return _scenario_action_response(_scenario_options(store_data), no_update, "")

        if trigger == "scenario-save-button":
            normalized_name = browser_store.validate_name(scenario_name or "")
            new_state = browser_store.save_scenario(
                store_data,
                normalized_name,
                browser_store.values_from_inputs(list(input_values)),
            )
            return _scenario_action_response(
                _scenario_options(new_state),
                normalized_name,
                f"«{normalized_name}» gespeichert. Ein gleichnamiges Szenario wird aktualisiert.",
                scenario_name_value=normalized_name,
                store_data=new_state,
            )

        if trigger == "scenario-load-button":
            if not selected_name:
                raise ValueError("Bitte wähle zuerst ein gespeichertes Szenario aus.")
            values = browser_store.load_scenario(store_data, selected_name)
            return _scenario_action_response(
                _scenario_options(store_data),
                selected_name,
                f"«{selected_name}» geladen.",
                values,
                scenario_name_value=selected_name,
            )

        if trigger == "scenario-delete-button":
            if not selected_name:
                raise ValueError("Bitte wähle zuerst ein gespeichertes Szenario aus.")
            new_state = browser_store.delete_scenario(store_data, selected_name)
            return _scenario_action_response(
                _scenario_options(new_state),
                None,
                f"«{selected_name}» gelöscht.",
                store_data=new_state,
            )

        return _scenario_action_response(no_update, no_update, "")
    except ValueError as error:
        return _scenario_action_response(
            _scenario_options(store_data),
            no_update,
            f"Aktion fehlgeschlagen: {error}",
            is_error=True,
        )


@app.callback(
    *[Output(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    Output(LAST_INPUTS_STORE_ID, "data"),
    Output("last-inputs-status", "children"),
    Input("last-inputs-initial-load", "n_intervals"),
    *[Input(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    State(LAST_INPUTS_STORE_ID, "data"),
)
def remember_dashboard_inputs(_initial_load, *args):
    """Restore the last inputs from this browser on load and remember later edits."""
    *input_values, store_data = args
    no_changes = [no_update] * len(SCENARIO_INPUT_IDS)
    try:
        if ctx.triggered_id == "last-inputs-initial-load":
            values = browser_store.read_last_inputs(store_data)
            if values is None:
                return [*no_changes, no_update, ""]
            return [*browser_store.values_to_inputs(values), no_update, ""]

        if ctx.triggered_id in SCENARIO_INPUT_IDS:
            values = browser_store.values_from_inputs(input_values)
            return [*no_changes, browser_store.make_last_inputs(values), ""]
        return [*no_changes, no_update, ""]
    except ValueError as error:
        return [
            *no_changes,
            no_update,
            html.Span(
                f"Letzte Eingaben konnten nicht gemerkt oder geladen werden: {error}",
                className="scenario-status-message scenario-status-error",
            ),
        ]


@app.callback(
    Output("pillar2-custom-fields", "style"),
    Input("pillar2-mode-input", "value"),
)
def update_pillar2_controls(mode):
    return {"display": "grid" if mode == "custom" else "none"}


@app.callback(
    Output("retirement-age-input", "options"),
    Output("retirement-age-input", "value"),
    Input("current-age-input", "value"),
    State("retirement-age-input", "value"),
)
def update_retirement_options(current_age, retirement_age):
    age = int(current_age or 35)
    minimum = max(config.MIN_RETIREMENT_AGE, age)
    options = [
        {"label": f"{value} Jahre", "value": value}
        for value in range(minimum, max(config.MAX_RETIREMENT_AGE, minimum) + 1)
    ]
    selected = retirement_age if retirement_age is not None and retirement_age >= minimum else minimum
    return options, selected


@app.callback(
    Output("income-label", "children"),
    Output("income-suffix", "children"),
    Output("income-hint", "children"),
    Output("canton-control", "style"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
)
def update_income_controls(period, income_type):
    period_label = "jährliches" if period == "yearly" else "monatliches"
    income_label = "Bruttoeinkommen" if income_type == "gross" else "Nettoeinkommen"
    suffix = "CHF/Jahr" if period == "yearly" else "CHF/Monat"
    hint = (
        "Betrag vor Abzügen; das Netto wird anhand deines Kantons geschätzt."
        if income_type == "gross"
        else "Frei verfügbares Einkommen nach Abzügen."
    )
    return (
        f"Dein {period_label} {income_label}",
        suffix,
        hint,
        {"display": "block" if income_type == "gross" else "none"},
    )


@app.callback(
    Output("income-preview", "children"),
    Input("monthly-income-input", "value"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
    Input("current-age-input", "value"),
    Input("canton-input", "value"),
)
def update_income_preview(amount, period, income_type, age, canton):
    try:
        monthly_net, monthly_gross = normalize_income(
            amount,
            period,
            income_type,
            int(age or 35),
            canton or "ZH",
        )
    except ValueError as error:
        return str(error)

    if income_type == "gross":
        return (
            f"Brutto {money(monthly_gross)}/Monat · geschätztes Netto "
            f"{money(monthly_net)}/Monat ({canton})"
        )
    return f"Für die Vorsorgeplanung verwendet: {money(monthly_net)} netto pro Monat"


@app.callback(
    Output("results-section", "children"),
    Output("calculation-notice", "children"),
    Input("monthly-income-input", "value"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
    Input("canton-input", "value"),
    Input("current-age-input", "value"),
    Input("retirement-age-input", "value"),
    Input("savings-mode-input", "value"),
    Input("pillar3a-rate-input", "value"),
    Input("pillar3a-amount-input", "value"),
    Input("pillar3b-amount-input", "value"),
    Input("pillar3a-initial-input", "value"),
    Input("pillar3b-initial-input", "value"),
    Input("pillar2-initial-input", "value"),
    Input("pillar2-mode-input", "value"),
    Input("pillar2-employee-input", "value"),
    Input("pillar2-employer-input", "value"),
    Input("pillar2-return-input", "value"),
    Input("return-input", "value"),
    Input("display-basis-input", "value"),
    Input("ahv-average-income-input", "value"),
    Input("ahv-contribution-years-input", "value"),
)
def update_results(
    income,
    income_period,
    income_type,
    canton,
    current_age,
    retirement_age,
    savings_mode,
    savings_rate,
    pillar3a_amount,
    pillar3b_amount,
    initial_3a,
    initial_3b,
    initial_2,
    pillar2_mode,
    pillar2_employee,
    pillar2_employer,
    pillar2_return,
    assumed_return,
    display_basis,
    ahv_average_income,
    ahv_contribution_years,
):
    def show_error(message: str):
        return (
            html.Div(
                [html.Strong("Eingaben prüfen"), html.P(message)],
                className="validation-message",
            ),
            "",
        )

    if current_age is None or retirement_age is None:
        return show_error("Bitte wähle dein aktuelles Alter und dein Pensionierungsalter.")
    if current_age < 18 or retirement_age < current_age:
        return show_error("Das Pensionierungsalter muss mindestens deinem aktuellen Alter entsprechen.")
    try:
        monthly_net_income, _ = normalize_income(
            income,
            income_period,
            income_type,
            int(current_age),
            canton,
        )
    except ValueError as error:
        return show_error(str(error))
    if monthly_net_income <= 0:
        return show_error(
            "Das geschätzte Nettoeinkommen beträgt 0 CHF. Bitte prüfe den Bruttobetrag."
        )
    if savings_mode not in {"rate", "amount"}:
        return show_error("Bitte wähle eine gültige Beitragsart für die 3a.")
    if savings_mode == "rate" and (
        savings_rate is None or not math.isfinite(float(savings_rate)) or not 0 <= savings_rate <= 100
    ):
        return show_error("Die Sparquote muss zwischen 0 und 100 Prozent liegen.")
    if savings_mode == "amount" and (
        pillar3a_amount is None
        or not math.isfinite(float(pillar3a_amount))
        or pillar3a_amount < 0
    ):
        return show_error("Der monatliche 3a-Beitrag muss mindestens 0 CHF betragen.")
    if pillar3b_amount is None or not math.isfinite(float(pillar3b_amount)) or pillar3b_amount < 0:
        return show_error("Der monatliche 3b-Beitrag muss mindestens 0 CHF betragen.")
    initial_3a = 0 if initial_3a is None else initial_3a
    initial_3b = 0 if initial_3b is None else initial_3b
    if not math.isfinite(float(initial_3a)) or initial_3a < 0:
        return show_error("Das aktuelle 3a-Guthaben muss mindestens 0 CHF betragen.")
    if not math.isfinite(float(initial_3b)) or initial_3b < 0:
        return show_error("Das aktuelle 3b-Guthaben muss mindestens 0 CHF betragen.")
    initial_2 = 0 if initial_2 is None else initial_2
    if not math.isfinite(float(initial_2)) or initial_2 < 0:
        return show_error("Das aktuelle BVG-Guthaben muss mindestens 0 CHF betragen.")
    if pillar2_mode not in {"minimum", "custom"}:
        return show_error("Bitte wähle eine Berechnungsgrundlage für die 2. Säule.")
    if pillar2_mode == "custom":
        if pillar2_employee is None or not math.isfinite(float(pillar2_employee)) or pillar2_employee < 0:
            return show_error("Der monatliche Arbeitnehmerbeitrag muss mindestens 0 CHF betragen.")
        if pillar2_employer is None or not math.isfinite(float(pillar2_employer)) or pillar2_employer < 0:
            return show_error("Der monatliche Arbeitgeberbeitrag muss mindestens 0 CHF betragen.")
        if pillar2_return is None or not math.isfinite(float(pillar2_return)) or not 0 <= pillar2_return <= 20:
            return show_error("Die Verzinsung der 2. Säule muss zwischen 0 und 20 Prozent liegen.")
    if assumed_return is None or assumed_return not in {0.02, 0.04, 0.06}:
        return show_error("Bitte wähle eine der angebotenen Renditeannahmen.")
    if display_basis not in {"nominal", "real"}:
        return show_error("Bitte wähle nominale oder reale Werte für die Prognose.")
    if ahv_average_income is not None and (
        not math.isfinite(float(ahv_average_income)) or ahv_average_income < 0
    ):
        return show_error("Das massgebende AHV-Jahreseinkommen muss mindestens 0 CHF betragen.")
    if (
        ahv_contribution_years is None
        or not math.isfinite(float(ahv_contribution_years))
        or not float(ahv_contribution_years).is_integer()
        or not 0 <= ahv_contribution_years <= ahv.FULL_CONTRIBUTION_YEARS
    ):
        return show_error(
            f"Die AHV-Beitragsjahre müssen eine ganze Zahl zwischen 0 und "
            f"{ahv.FULL_CONTRIBUTION_YEARS} sein."
        )

    calculator = FinanceCalculator(
        monthly_net_income=monthly_net_income,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        assumed_annual_return=float(assumed_return),
    )
    selected_rate = float(savings_rate) / 100 if savings_mode == "rate" else 0
    analysis = calculator.complete_analysis(pillar3a_savings_rate=selected_rate)
    if pillar2_mode == "custom":
        years = analysis.years_to_retirement
        employee_annual = float(pillar2_employee) * 12
        employer_annual = float(pillar2_employer) * 12
        pillar2_return_decimal = float(pillar2_return) / 100
        pillar2_capital = project_balance(
            employee_annual + employer_annual,
            years,
            pillar2_return_decimal,
            float(initial_2),
        )[-1]
        analysis.pillar2 = Pillar2Result(
            annual_contribution_employee=employee_annual,
            annual_contribution_employer=employer_annual,
            annual_contribution_total=employee_annual + employer_annual,
            coordination_deduction=0,
            insurable_salary=0,
            years_until_retirement=years,
            estimated_capital_at_retirement=pillar2_capital,
        )
    else:
        pillar2_return_decimal = config.ASSUMED_ANNUAL_RETURN
        analysis.pillar2.estimated_capital_at_retirement = project_balance(
            analysis.pillar2.annual_contribution_total,
            analysis.years_to_retirement,
            pillar2_return_decimal,
            float(initial_2),
        )[-1]
    if savings_mode == "rate":
        pillar3a = calculator.calculate_pillar3a(savings_rate=selected_rate)
        requested_3a_monthly = monthly_net_income * selected_rate
    else:
        pillar3a = calculator.calculate_pillar3a(monthly_amount=float(pillar3a_amount))
        requested_3a_monthly = float(pillar3a_amount)
    pillar3b = calculator.calculate_pillar3b(monthly_amount=float(pillar3b_amount))
    content, notice = results_view(
        income=monthly_net_income,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        assumed_return=float(assumed_return),
        analysis=analysis,
        pillar3a=pillar3a,
        pillar3b=pillar3b,
        pillar2_mode=pillar2_mode,
        pillar2_return=pillar2_return_decimal,
        initial_2=float(initial_2),
        initial_3a=float(initial_3a),
        initial_3b=float(initial_3b),
        display_basis=display_basis,
        ahv_average_income=(
            None if ahv_average_income is None else float(ahv_average_income)
        ),
        ahv_contribution_years=int(ahv_contribution_years),
    )
    if requested_3a_monthly > pillar3a.monthly_savings:
        notice = (
            f"Der eingegebene 3a-Beitrag wurde gemäss dem Modell-Limit auf "
            f"{money(pillar3a.monthly_savings)} pro Monat begrenzt."
        )
    return content, notice


# --- welcome notice and "delete all data in this browser" (issue #11) ----------------

NOTICE_VERSION = 1  # increase to show the notice again to everyone after a change


def _notice_acknowledged(store_data) -> bool:
    return isinstance(store_data, dict) and store_data.get("version") == NOTICE_VERSION and (
        store_data.get("acknowledged") is True
    )


@app.callback(
    Output("welcome-notice", "hidden"),
    Output(NOTICE_STORE_ID, "data"),
    Input("scenario-initial-load", "n_intervals"),
    Input("welcome-dismiss", "n_clicks"),
    Input("welcome-show", "n_clicks"),
    State(NOTICE_STORE_ID, "data"),
)
def toggle_welcome_notice(_initial_load, _dismiss_clicks, _show_clicks, store_data):
    """Show the notice until this browser has acknowledged it; reopen from the footer."""
    trigger = ctx.triggered_id
    if trigger == "welcome-dismiss":
        return True, {"version": NOTICE_VERSION, "acknowledged": True}
    if trigger == "welcome-show":
        return False, no_update
    return _notice_acknowledged(store_data), no_update


@app.callback(
    Output("clear-browser-data-confirm", "displayed"),
    Input("clear-browser-data-button", "n_clicks"),
    prevent_initial_call=True,
)
def ask_before_clearing_browser_data(_clicks):
    return True


# Runs in the browser only: removes every key of this app from localStorage and reloads.
app.clientside_callback(
    """
    function (confirmed) {
        if (!confirmed) { return window.dash_clientside.no_update; }
        Object.keys(window.localStorage)
            .filter(function (key) { return key.indexOf(%s) === 0; })
            .forEach(function (key) { window.localStorage.removeItem(key); });
        window.location.reload();
        return "";
    }
    """ % repr(STORAGE_KEY_PREFIX),
    Output("clear-browser-data-done", "children"),
    Input("clear-browser-data-confirm", "submit_n_clicks"),
    prevent_initial_call=True,
)
