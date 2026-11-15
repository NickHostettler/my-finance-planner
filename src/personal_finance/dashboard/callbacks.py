"""Dash callbacks. Importing this module registers them on the app.

Privacy rule: callbacks are pure request/response functions. User data arrives from the
user's own browser (inputs and ``dcc.Store`` state), is processed, and goes back only to
that browser. Nothing is written to disk, cached, kept in module state, or logged.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from dash import Input, Output, State, ctx, html, no_update

from personal_finance import config
from personal_finance.calculator import FinanceCalculator
from personal_finance.core import ahv
from personal_finance.core.home_plan import (
    HomeInputs,
    Pot,
    available_funds,
    plan_purchase,
    suggested_amounts,
)
from personal_finance.core.income import normalize_income
from personal_finance.core.pillar_2 import (
    Pillar2Result,
    estimated_contributions,
    growing_contributions,
    validate_salary_growth,
)
from personal_finance.core.projection import project_balance
from personal_finance.dashboard import home_view, life_view
from personal_finance.dashboard.app import app
from personal_finance.dashboard.components import (
    money,
    unit_width,
)
from personal_finance.dashboard.layout import (
    HOME_AMOUNT_HINTS,
    HOME_PREFILL_SKIP_STORE_ID,
    life_input_id,
    LAST_INPUTS_STORE_ID,
    NOTICE_STORE_ID,
    SCENARIOS_STORE_ID,
    STORAGE_KEY_PREFIX,
)
from personal_finance.dashboard.results import results_view
from personal_finance.storage import browser_store

RESULT_SECTION_IDS = [
    "overview-section",
    "pension-section",
    "home-section",
    "assumptions-section",
]


SCENARIO_INPUT_IDS = [
    "monthly-income-input",
    "income-period-input",
    "income-type-input",
    "canton-input",
    "current-age-input",
    "retirement-age-input",
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
    "home-plan-input",
    "home-price-input",
    "home-purchase-age-input",
    "home-savings-input",
    "home-pillar3a-input",
    "home-pillar2-input",
    "home-gross-income-input",
    "home-imputed-rate-input",
    "home-mortgage-rate-input",
    "home-amortisation-input",
    "salary-growth-input",
    # Life phases and family (v1.2): "life_1_to" -> "life-1-to-input", same order.
    *[life_input_id(field) for field in browser_store.LIFE_FIELDS],
]
# Same order as the stored fields (browser_store.SCENARIO_FIELDS).
_BASE_INPUT_COUNT = SCENARIO_INPUT_IDS.index("home-plan-input")

# The return switch (SegmentedControl) only knows text values; stored values are numbers.
_RETURN_INPUT_INDEX = SCENARIO_INPUT_IDS.index("return-input")


def _from_components(component_values):
    """Input values as stored: an emptied number field is ``None``, the return a number."""
    values = [None if value == "" else value for value in component_values]
    if isinstance(values[_RETURN_INPUT_INDEX], str):
        try:
            values[_RETURN_INPUT_INDEX] = float(values[_RETURN_INPUT_INDEX])
        except ValueError:
            values[_RETURN_INPUT_INDEX] = None
    return values


def _to_components(values):
    """Inverse of :func:`_from_components` for setting the input fields."""
    values = list(values)
    selected_return = values[_RETURN_INPUT_INDEX]
    values[_RETURN_INPUT_INDEX] = None if selected_return is None else str(selected_return)
    return values


# The highest monthly amount whose yearly total stays within the 3a maximum (rounded down to
# the 0.01 CHF step of the field).
PILLAR3A_MAX_MONTHLY_INPUT = math.floor(config.PILLAR3A_MONTHLY_MAX * 100) / 100


@app.callback(
    Output("pillar3a-amount-input", "value", allow_duplicate=True),
    Input("pillar3a-max-button", "n_clicks"),
    prevent_initial_call=True,
)
def fill_pillar3a_maximum(_clicks):
    """Put the highest possible monthly 3a amount into the field."""
    return PILLAR3A_MAX_MONTHLY_INPUT


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
        "scenario-status-message scenario-status-error" if is_error else "scenario-status-message"
    )
    status = html.Span(message, className=status_class) if message else ""
    if values is None:
        updated_values, skip = [no_update] * len(SCENARIO_INPUT_IDS), no_update
    else:
        updated_values, skip = (
            _to_components(browser_store.values_to_inputs(values)),
            (_prefill_skip(values)),
        )
    return [options, selected_name, status, scenario_name_value, *updated_values, skip, store_data]


def _prefill_skip(values) -> Dict[str, Any]:
    """What loading sets: the prefill leaves the loaded amounts alone for this change (#40)."""
    return {"plan": values["home_plan"], "age": values["home_purchase_age"]}


# Loading a scenario and restoring the last inputs both set the input fields, so those
# outputs are shared (allow_duplicate). Dash requires prevent_initial_call for that; the
# one-shot dcc.Interval still triggers both callbacks right after the page has loaded.
@app.callback(
    Output("scenario-select", "data"),
    Output("scenario-select", "value"),
    Output("scenario-status", "children"),
    Output("scenario-name-input", "value"),
    *[Output(component_id, "value", allow_duplicate=True) for component_id in SCENARIO_INPUT_IDS],
    Output(HOME_PREFILL_SKIP_STORE_ID, "data", allow_duplicate=True),
    Output(SCENARIOS_STORE_ID, "data"),
    Input("scenario-initial-load", "n_intervals"),
    Input("scenario-save-button", "n_clicks"),
    Input("scenario-load-button", "n_clicks"),
    Input("scenario-delete-button", "n_clicks"),
    State("scenario-name-input", "value"),
    State("scenario-select", "value"),
    State(SCENARIOS_STORE_ID, "data"),
    *[State(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    prevent_initial_call=True,
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
                browser_store.values_from_inputs(_from_components(input_values)),
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
    *[Output(component_id, "value", allow_duplicate=True) for component_id in SCENARIO_INPUT_IDS],
    Output(HOME_PREFILL_SKIP_STORE_ID, "data", allow_duplicate=True),
    Input("last-inputs-initial-load", "n_intervals"),
    State(LAST_INPUTS_STORE_ID, "data"),
    prevent_initial_call=True,
)
def restore_last_inputs(_initial_load, store_data):
    """Fill the input fields with the inputs this browser remembered last time."""
    values = browser_store.read_last_inputs(store_data)
    if values is None:
        return [no_update] * (len(SCENARIO_INPUT_IDS) + 1)
    return [*_to_components(browser_store.values_to_inputs(values)), _prefill_skip(values)]


# Separate from restoring, so that no callback reads and writes the same fields (a cycle that
# left Dash waiting forever with the Mantine fields).
@app.callback(
    Output(LAST_INPUTS_STORE_ID, "data"),
    Output("last-inputs-status", "children"),
    *[Input(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    prevent_initial_call=True,
)
def remember_dashboard_inputs(*component_values):
    """Remember every change of the inputs in this browser (localStorage)."""
    try:
        values = browser_store.values_from_inputs(_from_components(component_values))
    except ValueError as error:
        return no_update, html.Span(
            f"Letzte Eingaben konnten nicht gemerkt werden: {error}",
            className="scenario-status-message scenario-status-error",
        )
    return browser_store.make_last_inputs(values), ""


@app.callback(
    Output("pillar2-custom-fields", "style"),
    Input("pillar2-mode-input", "value"),
)
def update_pillar2_controls(mode):
    return {"display": "grid" if mode == "custom" else "none"}


@app.callback(
    Output("home-fields", "style"),
    Input("home-plan-input", "value"),
)
def update_home_controls(plan):
    """Show the home ownership fields only while a purchase is planned."""
    return {"display": "grid" if plan == "on" else "none"}


# --- life phases: show the used rows (#33) -----------------------------------------------

_LIFE_WORKLOAD_IDS = [life_input_id(f"life_{row}_workload") for row in life_view.ROWS]
_LIFE_TO_IDS = [life_input_id(f"life_{row}_to") for row in life_view.ROWS]


@app.callback(
    Output("life-fields", "style"),
    *[Output(f"life-row-{row}", "style") for row in life_view.ROWS],
    *[Output(f"life-row-{row}-to", "style") for row in life_view.ROWS],
    *[Output(f"life-row-{row}-title", "children") for row in life_view.ROWS],
    Input("life-plan-input", "value"),
    Input("current-age-input", "value"),
    *[Input(component_id, "value") for component_id in _LIFE_WORKLOAD_IDS],
    *[Input(component_id, "value") for component_id in _LIFE_TO_IDS],
)
def update_life_controls(plan, current_age, *values):
    """Show the phase rows in use (at least one); the last one needs no «bis Alter»."""
    rows = len(life_view.ROWS)
    workloads, to_ages = values[:rows], values[rows:]
    visible = max(1, life_view.used_rows(workloads))
    return [
        {"display": "grid" if plan == "on" else "none"},
        *[{"display": "block" if row <= visible else "none"} for row in life_view.ROWS],
        *[{"display": "none" if row == visible else "block"} for row in life_view.ROWS],
        *life_view.row_titles(current_age, to_ages, visible),
    ]


# --- purchase money: fill in the highest amounts at the purchase age (#40) -----------

HOME_AMOUNT_IDS = list(HOME_AMOUNT_HINTS)  # savings, 3a, pension fund
_PREFILL_TRIGGER_IDS = ["home-plan-input", "home-purchase-age-input"]
# Everything the projection needs; the amounts themselves are not read (no cycle).
_PREFILL_STATE_IDS = [
    component_id
    for component_id in SCENARIO_INPUT_IDS
    if component_id not in HOME_AMOUNT_IDS + _PREFILL_TRIGGER_IDS
]
_HINT_INPUT_IDS = [
    component_id for component_id in SCENARIO_INPUT_IDS if component_id not in HOME_AMOUNT_IDS
]


def _home_maximum(values_by_id):
    """Available funds and suggested amounts for the planned purchase, or ``None``.

    ``None`` if no purchase is planned or the inputs are not valid (the result tabs explain
    the error).
    """
    values = _from_components(
        [values_by_id.get(component_id) for component_id in SCENARIO_INPUT_IDS]
    )
    try:
        base = _projection(values)
        if base.values["home_plan"] != "on":
            return None
        available = available_funds(
            base.values["home_purchase_age"], base.current_age, base.retirement_age, *base.pots
        )
        return available, suggested_amounts(base.values["home_price"], available)
    except ValueError:
        return None


@app.callback(
    *[Output(component_id, "value", allow_duplicate=True) for component_id in HOME_AMOUNT_IDS],
    Output(HOME_PREFILL_SKIP_STORE_ID, "data", allow_duplicate=True),
    Input("home-plan-input", "value"),
    Input("home-purchase-age-input", "value"),
    Input("home-max-button", "n_clicks"),
    State(HOME_PREFILL_SKIP_STORE_ID, "data"),
    *[State(component_id, "value") for component_id in _PREFILL_STATE_IDS],
    prevent_initial_call=True,
)
def fill_home_maximum(plan, age, _clicks, skip, *other_values):
    """Put the highest amounts at the purchase age into the purchase money fields.

    Runs when the purchase is planned, when the purchase age changes and on the button. When
    a loaded scenario or the remembered inputs set the purchase (``skip``), their amounts stay.
    The amounts are capped at what the purchase needs (see ``suggested_amounts``).
    """
    unchanged = [no_update] * len(HOME_AMOUNT_IDS)
    age = None if age == "" else age
    loaded = ctx.triggered_id != "home-max-button" and skip == {"plan": plan, "age": age}
    if plan != "on" or loaded:
        return [*unchanged, None]
    values_by_id = dict(zip(_PREFILL_STATE_IDS, other_values))
    values_by_id.update({"home-plan-input": plan, "home-purchase-age-input": age})
    result = _home_maximum(values_by_id)
    if result is None:
        return [*unchanged, None]
    return [*result[1], None]


@app.callback(
    *[Output(component_id, "description") for component_id in HOME_AMOUNT_IDS],
    *[Input(component_id, "value") for component_id in _HINT_INPUT_IDS],
)
def update_home_amount_hints(*component_values):
    """Show the highest amount at the purchase age below each purchase money field."""
    defaults = [HOME_AMOUNT_HINTS[component_id] for component_id in HOME_AMOUNT_IDS]
    result = _home_maximum(dict(zip(_HINT_INPUT_IDS, component_values)))
    if result is None:
        return defaults
    available = result[0]
    savings_hint, pillar3a_hint, pillar2_hint = (hint[0].lower() + hint[1:] for hint in defaults)
    return [
        f"Freies Vermögen zum Kaufalter: {money(available.savings)} · {savings_hint}",
        f"3a zum Kaufalter: {money(available.pillar3a)} · {pillar3a_hint}",
        (
            f"Höchstens {money(available.pillar2)} zum Kaufalter · {pillar2_hint}"
            if available.pillar2 > 0
            else f"Zum Kaufalter kein Vorbezug möglich · {pillar2_hint}"
        ),
    ]


@app.callback(
    Output("monthly-income-input", "label"),
    Output("monthly-income-input", "rightSection"),
    Output("monthly-income-input", "rightSectionWidth"),
    Output("monthly-income-input", "description"),
    Output("canton-control", "style"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
)
def update_income_controls(period, income_type):
    period_label = "jährliches" if period == "yearly" else "monatliches"
    income_label = "Bruttoeinkommen" if income_type == "gross" else "Nettoeinkommen"
    unit = "CHF/Jahr" if period == "yearly" else "CHF/Monat"
    hint = (
        "Betrag vor Abzügen; das Netto wird anhand deines Kantons geschätzt."
        if income_type == "gross"
        else "Frei verfügbares Einkommen nach Abzügen."
    )
    return (
        f"Dein {period_label} {income_label}",
        unit,
        unit_width(unit),
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


@dataclass(frozen=True)
class _Projection:
    """The validated general inputs and the projection without a purchase."""

    values: Dict[str, Any]  # all inputs by field name (browser_store.SCENARIO_FIELDS)
    current_age: int
    retirement_age: int
    monthly_net_income: float
    monthly_gross_income: float
    salary_growth: float
    analysis: Any
    pillar3a: Any
    pillar3b: Any
    pillar2_return: float
    pots: Tuple[Pot, Pot, Pot]
    ahv_average_income: Optional[float]
    ahv_contribution_years: int

    @property
    def income_is_net(self) -> bool:
        return self.values["income_type"] != "gross"

    @property
    def income_annual(self) -> float:
        monthly = self.monthly_net_income if self.income_is_net else self.monthly_gross_income
        return monthly * 12


def _projection(values) -> _Projection:
    """Validate the inputs (in SCENARIO_INPUT_IDS order) and project the pots.

    Raises ``ValueError`` with the message for the user.
    """
    (
        income,
        income_period,
        income_type,
        canton,
        current_age,
        retirement_age,
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
    ) = values[:_BASE_INPUT_COUNT]
    fields = dict(zip(browser_store.SCENARIO_FIELDS, values))

    if current_age is None or retirement_age is None:
        raise ValueError("Bitte wähle dein aktuelles Alter und dein Pensionierungsalter.")
    if current_age < 18 or retirement_age < current_age:
        raise ValueError(
            "Das Pensionierungsalter muss mindestens deinem aktuellen Alter entsprechen."
        )
    monthly_net_income, monthly_gross_income = normalize_income(
        income,
        income_period,
        income_type,
        int(current_age),
        canton,
    )
    if monthly_net_income <= 0:
        raise ValueError(
            "Das geschätzte Nettoeinkommen beträgt 0 CHF. Bitte prüfe den Bruttobetrag."
        )
    salary_growth = validate_salary_growth(_percent_to_rate(fields["salary_growth"]))
    if pillar3a_amount is None or not math.isfinite(float(pillar3a_amount)) or pillar3a_amount < 0:
        raise ValueError("Der monatliche 3a-Beitrag muss mindestens 0 CHF betragen.")
    if pillar3b_amount is None or not math.isfinite(float(pillar3b_amount)) or pillar3b_amount < 0:
        raise ValueError("Der monatliche 3b-Beitrag muss mindestens 0 CHF betragen.")
    initial_3a = 0 if initial_3a is None else initial_3a
    initial_3b = 0 if initial_3b is None else initial_3b
    if not math.isfinite(float(initial_3a)) or initial_3a < 0:
        raise ValueError("Das aktuelle 3a-Guthaben muss mindestens 0 CHF betragen.")
    if not math.isfinite(float(initial_3b)) or initial_3b < 0:
        raise ValueError("Das aktuelle 3b-Guthaben muss mindestens 0 CHF betragen.")
    initial_2 = 0 if initial_2 is None else initial_2
    if not math.isfinite(float(initial_2)) or initial_2 < 0:
        raise ValueError("Das aktuelle BVG-Guthaben muss mindestens 0 CHF betragen.")
    if pillar2_mode not in {"minimum", "custom"}:
        raise ValueError("Bitte wähle eine Berechnungsgrundlage für die 2. Säule.")
    if pillar2_mode == "custom":
        if (
            pillar2_employee is None
            or not math.isfinite(float(pillar2_employee))
            or pillar2_employee < 0
        ):
            raise ValueError("Der monatliche Arbeitnehmerbeitrag muss mindestens 0 CHF betragen.")
        if (
            pillar2_employer is None
            or not math.isfinite(float(pillar2_employer))
            or pillar2_employer < 0
        ):
            raise ValueError("Der monatliche Arbeitgeberbeitrag muss mindestens 0 CHF betragen.")
        if (
            pillar2_return is None
            or not math.isfinite(float(pillar2_return))
            or not 0 <= pillar2_return <= 20
        ):
            raise ValueError("Die Verzinsung der 2. Säule muss zwischen 0 und 20 Prozent liegen.")
    if assumed_return is None or assumed_return not in {0.02, 0.04, 0.06}:
        raise ValueError("Bitte wähle eine der angebotenen Renditeannahmen.")
    if display_basis not in {"nominal", "real"}:
        raise ValueError("Bitte wähle nominale oder reale Werte für die Prognose.")
    if ahv_average_income is not None and (
        not math.isfinite(float(ahv_average_income)) or ahv_average_income < 0
    ):
        raise ValueError("Das massgebende AHV-Jahreseinkommen muss mindestens 0 CHF betragen.")
    if (
        ahv_contribution_years is None
        or not math.isfinite(float(ahv_contribution_years))
        or not float(ahv_contribution_years).is_integer()
        or not 0 <= ahv_contribution_years <= ahv.FULL_CONTRIBUTION_YEARS
    ):
        raise ValueError(
            f"Die AHV-Beitragsjahre müssen eine ganze Zahl zwischen 0 und "
            f"{ahv.FULL_CONTRIBUTION_YEARS} sein."
        )

    calculator = FinanceCalculator(
        monthly_net_income=monthly_net_income,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        assumed_annual_return=float(assumed_return),
    )
    analysis = calculator.complete_analysis(pillar3a_savings_rate=0)
    years = analysis.years_to_retirement
    # The contributions to the 2nd pillar rise with the salary, year by year.
    if pillar2_mode == "custom":
        employee_annual = float(pillar2_employee) * 12
        employer_annual = float(pillar2_employer) * 12
        pillar2_return_decimal = float(pillar2_return) / 100
        pillar2_contributions = growing_contributions(
            employee_annual + employer_annual, years, salary_growth
        )
        pillar2_capital = project_balance(
            pillar2_contributions,
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
            annual_contributions=pillar2_contributions,
        )
    else:
        pillar2_return_decimal = config.ASSUMED_ANNUAL_RETURN
        pillar2_contributions = estimated_contributions(
            monthly_net_income * 12, int(current_age), years, salary_growth
        )
        analysis.pillar2.annual_contributions = pillar2_contributions
        analysis.pillar2.estimated_capital_at_retirement = project_balance(
            pillar2_contributions,
            years,
            pillar2_return_decimal,
            float(initial_2),
        )[-1]
    pillar3a = calculator.calculate_pillar3a(monthly_amount=float(pillar3a_amount))
    pillar3b = calculator.calculate_pillar3b(monthly_amount=float(pillar3b_amount))
    return _Projection(
        values=fields,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        monthly_net_income=monthly_net_income,
        monthly_gross_income=monthly_gross_income,
        salary_growth=salary_growth,
        analysis=analysis,
        pillar3a=pillar3a,
        pillar3b=pillar3b,
        pillar2_return=pillar2_return_decimal,
        pots=(
            Pot(pillar2_contributions, pillar2_return_decimal, float(initial_2)),
            Pot(pillar3a.annual_savings, float(assumed_return), float(initial_3a)),
            Pot(pillar3b.annual_savings, float(assumed_return), float(initial_3b)),
        ),
        ahv_average_income=(None if ahv_average_income is None else float(ahv_average_income)),
        ahv_contribution_years=int(ahv_contribution_years),
    )


@app.callback(
    *[Output(section_id, "children") for section_id in RESULT_SECTION_IDS],
    Output("calculation-notice", "children"),
    *[Input(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
)
def update_results(*component_values):
    """Validate the inputs and render the result tabs (inputs in SCENARIO_INPUT_IDS order)."""
    try:
        base = _projection(_from_components(component_values))
    except ValueError as error:
        message = html.Div(
            [html.Strong("Eingaben prüfen"), html.P(str(error))],
            className="validation-message",
        )
        return message, message, message, message, ""

    values = base.values
    plan, home = _home_results(
        values,
        current_age=base.current_age,
        retirement_age=base.retirement_age,
        income_annual=base.income_annual,
        income_is_net=base.income_is_net,
        pots=base.pots,
        display_basis=values["display_basis"],
        ahv_annual_at_retirement=_ahv_annual(base),
    )
    overview, pension, assumptions, notice = results_view(
        income=base.monthly_net_income,
        current_age=base.current_age,
        retirement_age=base.retirement_age,
        assumed_return=float(values["assumed_return"]),
        analysis=base.analysis,
        pillar3a=base.pillar3a,
        pillar3b=base.pillar3b,
        pillar2_mode=values["pillar2_mode"],
        pillar2_return=base.pillar2_return,
        initial_2=base.pots[0].initial,
        initial_3a=base.pots[1].initial,
        initial_3b=base.pots[2].initial,
        display_basis=values["display_basis"],
        salary_growth=base.salary_growth,
        ahv_average_income=base.ahv_average_income,
        ahv_contribution_years=base.ahv_contribution_years,
        paths=None if plan is None else plan.with_purchase,
        purchase_note=None if plan is None else plan.withdrawal_note(),
    )
    if float(values["pillar3a_amount"]) > base.pillar3a.monthly_savings:
        notice = (
            f"Der eingegebene 3a-Beitrag wurde gemäss dem Modell-Limit auf "
            f"{money(base.pillar3a.monthly_savings)} pro Monat begrenzt."
        )
    return overview, pension, home, assumptions, notice


def _ahv_annual(base: _Projection) -> Optional[float]:
    """Nominal AHV per year at retirement (13 pensions), like the overview card."""
    if base.ahv_average_income is None:
        return None
    return 13 * ahv.project_pension_basis(
        ahv.estimate_monthly_old_age_pension(base.ahv_average_income, base.ahv_contribution_years),
        base.analysis.years_to_retirement,
        config.INFLATION_RATE,
        "nominal",
    )


def _percent_to_rate(value):
    """Percent from an input field as a decimal; anything else is passed on for validation."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value / 100
    return value


def _home_results(
    values,
    current_age,
    retirement_age,
    income_annual,
    income_is_net,
    pots,
    display_basis,
    ahv_annual_at_retirement,
):
    """The planned purchase (``None`` if none or invalid) and the "Wohneigentum" tab."""
    if values["home_plan"] != "on":
        return None, home_view.home_section(None)
    inputs = HomeInputs(
        price=values["home_price"],
        savings=values["home_savings"],
        pillar3a=values["home_pillar3a"],
        pillar2=values["home_pillar2"],
        purchase_age=values["home_purchase_age"],
        gross_income=values["home_gross_income"],
        imputed_rate=_percent_to_rate(values["home_imputed_rate"]),
        mortgage_rate=_percent_to_rate(values["home_mortgage_rate"]),
        amortisation=values["home_amortisation"],
    )
    try:
        plan = plan_purchase(
            inputs,
            current_age,
            retirement_age,
            income_annual,
            income_is_net,
            *pots,
            ahv_annual_at_retirement=ahv_annual_at_retirement,
        )
    except ValueError as error:
        return None, home_view.home_section(None, str(error))
    return plan, home_view.home_section(plan, display_basis=display_basis)


# Phones: the burger in the header shows or hides the inputs column (runs in the browser).
app.clientside_callback(
    """
    function (isOpen, navbar) {
        return Object.assign({}, navbar, {collapsed: {mobile: !isOpen}});
    }
    """,
    Output("app-shell", "navbar"),
    Input("navbar-burger", "opened"),
    State("app-shell", "navbar"),
)


# --- welcome notice and "delete all data in this browser" (issue #11) ----------------

NOTICE_VERSION = 1  # increase to show the notice again to everyone after a change


def _notice_acknowledged(store_data) -> bool:
    return (
        isinstance(store_data, dict)
        and store_data.get("version") == NOTICE_VERSION
        and (store_data.get("acknowledged") is True)
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
    """
    % repr(STORAGE_KEY_PREFIX),
    Output("clear-browser-data-done", "children"),
    Input("clear-browser-data-confirm", "submit_n_clicks"),
    prevent_initial_call=True,
)
