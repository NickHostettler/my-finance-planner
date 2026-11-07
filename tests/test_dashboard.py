"""Tests for dashboard income input normalization."""

import pytest

from personal_finance.dashboard import (
    _chart_card,
    _money,
    _normalize_income,
    _projection_values,
    SCENARIO_INPUT_IDS,
    app,
    update_results,
    update_pillar2_controls,
    update_savings_controls,
)
from personal_finance import ahv, config


def _update_dashboard(
    *,
    initial_3a=0,
    initial_3b=0,
    initial_2=0,
    pillar2_mode="minimum",
    pillar2_employee=300,
    pillar2_employer=300,
    pillar2_return=1.25,
    display_basis="nominal",
    ahv_average_income=None,
    ahv_contribution_years=44,
):
    return update_results(
        5000,
        "monthly",
        "net",
        "ZH",
        35,
        65,
        "amount",
        10,
        350,
        500,
        initial_3a,
        initial_3b,
        initial_2,
        pillar2_mode,
        pillar2_employee,
        pillar2_employer,
        pillar2_return,
        0.04,
        display_basis,
        ahv_average_income,
        ahv_contribution_years,
    )


@pytest.mark.parametrize(
    ("period", "amount", "expected_monthly_net"),
    [
        ("monthly", 5000, 5000),
        ("yearly", 60000, 5000),
    ],
)
def test_net_income_is_normalized_to_monthly(period, amount, expected_monthly_net):
    monthly_net, _ = _normalize_income(amount, period, "net", 35, "ZH")

    assert monthly_net == expected_monthly_net


def test_gross_income_is_converted_to_estimated_net():
    monthly_net, monthly_gross = _normalize_income(7500, "monthly", "gross", 35, "ZH")

    assert monthly_gross == 7500
    assert 0 < monthly_net < monthly_gross


def test_yearly_and_monthly_gross_income_produce_same_estimate():
    monthly_result = _normalize_income(7500, "monthly", "gross", 35, "ZH")
    yearly_result = _normalize_income(90000, "yearly", "gross", 35, "ZH")

    assert yearly_result == monthly_result


def test_screenshot_income_values_produce_valid_net_income():
    monthly_net, monthly_gross = _normalize_income(120000, "yearly", "gross", 30, "LU")

    assert monthly_gross == 10000
    assert monthly_net > 0


def test_income_input_accepts_round_hundreds():
    income_input = next(
        component
        for component in app.layout._traverse()
        if getattr(component, "id", None) == "monthly-income-input"
    )

    assert income_input.min == 0
    assert income_input.step == 100


def test_3a_amount_input_accepts_model_limit():
    amount_input = next(
        component
        for component in app.layout._traverse()
        if getattr(component, "id", None) == "pillar3a-amount-input"
    )

    assert amount_input.min == 0
    assert amount_input.step == 0.01
    assert amount_input.max == pytest.approx(config.PILLAR3A_ANNUAL_MAX / 12)
    assert amount_input.max * 12 == pytest.approx(7258)


@pytest.mark.parametrize(
    ("input_id", "expected_step"),
    [
        ("pillar3a-initial-input", 1000),
        ("pillar3b-initial-input", 1000),
        ("pillar2-initial-input", 1000),
    ],
)
def test_current_pillar_balances_are_optional_nonnegative_inputs(input_id, expected_step):
    balance_input = next(
        component
        for component in app.layout._traverse()
        if getattr(component, "id", None) == input_id
    )

    assert balance_input.value == 0
    assert balance_input.min == 0
    assert balance_input.step == expected_step


def test_custom_pillar2_inputs_start_blank():
    for input_id in (
        "pillar2-employee-input",
        "pillar2-employer-input",
        "pillar2-return-input",
    ):
        component = next(
            item
            for item in app.layout._traverse()
            if getattr(item, "id", None) == input_id
        )

        assert component.value is None


def test_ahv_estimate_inputs_default_to_last_entered_values():
    inputs = {
        component.id: component
        for component in app.layout._traverse()
        if getattr(component, "id", None)
        in {"ahv-average-income-input", "ahv-contribution-years-input"}
    }

    assert inputs["ahv-average-income-input"].value == 100000
    assert inputs["ahv-contribution-years-input"].value == 44


def test_scenario_controls_are_available_in_dashboard():
    component_ids = {
        getattr(component, "id", None)
        for component in app.layout._traverse()
        if getattr(component, "id", None)
    }

    assert {
        "scenario-name-input",
        "scenario-save-button",
        "scenario-select",
        "scenario-load-button",
        "scenario-delete-button",
        "scenario-status",
        "last-inputs-initial-load",
        "last-inputs-status",
        "display-basis-input",
    }.issubset(component_ids)
    assert app.server.test_client().get("/_dash-layout").status_code == 200


def test_last_input_callback_covers_every_scenario_input():
    callback = next(
        callback
        for callback in app.callback_map.values()
        if callback["callback"].__name__ == "remember_dashboard_inputs"
    )

    input_ids = {item["id"] for item in callback["inputs"]}
    assert set(SCENARIO_INPUT_IDS).issubset(input_ids)


def test_nominal_real_selection_defaults_to_nominal_and_is_saved_with_scenario_inputs():
    selection = next(
        component
        for component in app.layout._traverse()
        if getattr(component, "id", None) == "display-basis-input"
    )

    assert selection.value == "nominal"
    assert {option["value"] for option in selection.options} == {"nominal", "real"}
    assert "display-basis-input" in SCENARIO_INPUT_IDS
    assert {
        "ahv-average-income-input",
        "ahv-contribution-years-input",
    }.issubset(SCENARIO_INPUT_IDS)
    assert "ahv-manual-monthly-input" not in SCENARIO_INPUT_IDS


def test_initial_balance_compounds_until_retirement():
    values = _projection_values(0, years=2, annual_return=0.04, initial_balance=10000)

    assert values == pytest.approx([10000, 10400, 10816])


def test_real_projection_converts_nominal_future_value_to_todays_purchasing_power():
    nominal = _projection_values(1000, years=2, annual_return=0.04)
    real = _projection_values(
        1000,
        years=2,
        annual_return=0.04,
        inflation_rate=config.INFLATION_RATE,
    )

    assert nominal[-1] == pytest.approx(2121.6)
    assert real[-1] == pytest.approx(nominal[-1] / (1 + config.INFLATION_RATE) ** 2)
    assert real[0] == nominal[0]


def test_real_display_switch_updates_cards_charts_and_assumptions():
    nominal_content, _ = _update_dashboard()
    real_content, _ = _update_dashboard(display_basis="real")

    def metric_values(content):
        return [
            component.children
            for component in content[0]._traverse()
            if getattr(component, "className", None) == "metric-value"
        ]

    nominal_metrics = metric_values(nominal_content)
    real_metrics = metric_values(real_content)
    assert real_metrics[0] != nominal_metrics[0]
    assert real_metrics[1] != nominal_metrics[1]
    assert real_metrics[2] != nominal_metrics[2]
    assert real_metrics[3] != nominal_metrics[3]

    real_figures = [
        component.figure
        for component in real_content[0]._traverse()
        if component.__class__.__name__ == "Graph"
    ]
    nominal_figures = [
        component.figure
        for component in nominal_content[0]._traverse()
        if component.__class__.__name__ == "Graph"
    ]
    growth_figure = next(figure for figure in real_figures if figure.data[0].type == "scatter")
    nominal_growth = next(figure for figure in nominal_figures if figure.data[0].type == "scatter")
    comparison_figure = next(figure for figure in real_figures if figure.data[0].type == "bar")
    assert growth_figure.data[0].y[0] == nominal_growth.data[0].y[0]
    assert growth_figure.data[0].y[-1] < nominal_growth.data[0].y[-1]

    def parse_money(value):
        return float(value.replace("CHF ", "").replace("’", "").replace(",", ""))

    assert comparison_figure.data[0].x[3] == pytest.approx(parse_money(real_metrics[0]))

    text = " ".join(
        component.children
        for component in real_content[0]._traverse()
        if isinstance(getattr(component, "children", None), str)
    )
    assert "heutiger Kaufkraft" in text
    assert f"{config.INFLATION_RATE:.0%} Inflation pro Jahr" in text
    assert "von den zukünftigen Kapitalwerten abgezogen" in text


def test_results_include_starting_balances_in_retirement_projection():
    without_starting_balance, _ = _update_dashboard()
    with_starting_balance, _ = _update_dashboard(
        initial_2=15000, initial_3a=10000, initial_3b=20000
    )

    def metric_values(result):
        return [
            component.children
            for component in result[0]._traverse()
            if getattr(component, "className", None) == "metric-value"
        ]

    without = metric_values(without_starting_balance)
    with_balances = metric_values(with_starting_balance)

    assert len(without) == len(with_balances) == 5
    assert with_balances[0] != without[0]
    assert with_balances[2] != without[2]
    assert with_balances[3] != without[3]

    figures = [
        component.figure
        for component in with_starting_balance[0]._traverse()
        if component.__class__.__name__ == "Graph"
    ]
    growth_figure = next(figure for figure in figures if figure.data[0].type == "scatter")
    comparison_figure = next(figure for figure in figures if figure.data[0].type == "bar")
    composition_figure = next(figure for figure in figures if figure.data[0].type == "pie")

    assert growth_figure.data[0].y[0] == 15000
    assert growth_figure.data[1].y[0] == 10000
    assert growth_figure.data[2].y[0] == 20000
    assert comparison_figure.data[0].x[1] > 0
    assert comparison_figure.data[0].x[2] > 0
    assert composition_figure.data[0].labels[0] == "Bisheriges Startguthaben"
    assert composition_figure.data[0].values[0] == 45000


def test_empty_starting_balances_are_treated_as_zero():
    with_empty_balances, notice = _update_dashboard(initial_3a=None, initial_2=None, initial_3b=None)

    assert notice == ""
    assert with_empty_balances


@pytest.mark.parametrize(
    ("income", "years", "expected"),
    [
        (ahv.MINIMUM_PENSION_INCOME, 44, ahv.MINIMUM_FULL_MONTHLY_PENSION),
        (ahv.MAXIMUM_PENSION_INCOME, 44, ahv.MAXIMUM_FULL_MONTHLY_PENSION),
        (ahv.MAXIMUM_PENSION_INCOME, 22, ahv.MAXIMUM_FULL_MONTHLY_PENSION / 2),
        (0, 0, 0),
    ],
)
def test_ahv_estimate_interpolates_official_scale_bounds(income, years, expected):
    assert ahv.estimate_monthly_old_age_pension(income, years) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("income", "years"),
    [(-1, 44), (float("nan"), 44), (20000, -1), (20000, 45), (20000, 10.5)],
)
def test_ahv_estimate_rejects_invalid_values(income, years):
    with pytest.raises(ValueError):
        ahv.estimate_monthly_old_age_pension(income, years)


def test_ahv_rent_is_separate_and_projected_in_nominal_or_real_basis():
    without_ahv, _ = _update_dashboard()
    nominal, _ = _update_dashboard(
        ahv_average_income=ahv.MAXIMUM_PENSION_INCOME,
        ahv_contribution_years=44,
    )
    real, _ = _update_dashboard(
        display_basis="real",
        ahv_average_income=ahv.MAXIMUM_PENSION_INCOME,
        ahv_contribution_years=44,
    )

    def values_and_details(content):
        components = list(content[0]._traverse())
        values = [
            component.children
            for component in components
            if getattr(component, "className", None) == "metric-value"
        ]
        details = [
            component.children
            for component in components
            if getattr(component, "className", None) == "metric-detail"
        ]
        return values, details

    nominal_values, nominal_details = values_and_details(nominal)
    real_values, real_details = values_and_details(real)
    without_ahv_values, _ = values_and_details(without_ahv)

    assert nominal_values[0] == without_ahv_values[0]
    assert nominal_values[4] != real_values[4]
    assert nominal_details[4] != real_details[4]
    assert "CHF 2’520" in real_values[4]
    assert "CHF 32’760" in real_details[4]


@pytest.mark.parametrize(
    ("average_income", "years", "message"),
    [
        (float("inf"), 44, "AHV-Jahreseinkommen"),
        (None, 44.5, "Beitragsjahre"),
    ],
)
def test_dashboard_rejects_invalid_ahv_inputs(average_income, years, message):
    result, notice = _update_dashboard(
        ahv_average_income=average_income,
        ahv_contribution_years=years,
    )

    assert result.__class__.__name__ == "Div"
    assert message in result.children[1].children
    assert notice == ""


@pytest.mark.parametrize(
    ("mode", "expected_display"),
    [("minimum", "none"), ("custom", "grid")],
)
def test_pillar2_custom_inputs_follow_selected_mode(mode, expected_display):
    assert update_pillar2_controls(mode)["display"] == expected_display


def test_custom_pillar2_contributions_and_interest_are_projected():
    content, notice = _update_dashboard(
        initial_2=10000,
        pillar2_mode="custom",
        pillar2_employee=100,
        pillar2_employer=200,
        pillar2_return=2,
    )

    assert notice == ""
    result = content[0]
    figures = [
        component.figure
        for component in result._traverse()
        if component.__class__.__name__ == "Graph"
    ]
    growth_figure = next(figure for figure in figures if figure.data[0].type == "scatter")
    comparison_figure = next(figure for figure in figures if figure.data[0].type == "bar")
    composition_figure = next(figure for figure in figures if figure.data[0].type == "pie")
    expected_capital = _projection_values(3600, 30, 0.02, 10000)[-1]

    assert growth_figure.data[0].y[0] == 10000
    assert growth_figure.data[0].y[-1] == pytest.approx(expected_capital)
    assert comparison_figure.data[0].x[0] == pytest.approx(expected_capital)
    assert composition_figure.data[0].values[0] == 10000

    metric_details = [
        component.children
        for component in result._traverse()
        if getattr(component, "className", None) == "metric-detail"
    ]
    assert "AN CHF 100" in metric_details[1]
    assert "AG CHF 200" in metric_details[1]


@pytest.mark.parametrize(
    ("mode", "expected_assumption"),
    [
        ("minimum", "Keine offizielle BVG-Mindestberechnung"),
        ("custom", "Deine angegebenen Beiträge ersetzen die vereinfachte Schätzung"),
    ],
)
def test_model_assumptions_disclose_pillar2_method_and_inflation(mode, expected_assumption):
    content, notice = _update_dashboard(pillar2_mode=mode)
    assert notice == ""
    result = content[0]
    assumption_text = [
        component.children
        for component in result._traverse()
        if isinstance(getattr(component, "children", None), str)
    ]
    joined_text = " ".join(assumption_text)

    assert expected_assumption in joined_text
    assert f"{config.INFLATION_RATE:.0%} Inflation pro Jahr" in joined_text
    assert "nicht abgezogen" in joined_text
    assert "nominal" in joined_text
    assert f"{config.ASSUMED_ANNUAL_RETURN:.0%} pro Jahr" in joined_text
    assert f"{_money(config.PILLAR3A_ANNUAL_MAX)} pro Jahr" in joined_text
    assert "AHV-Rente" in joined_text


def test_pillar2_interest_assumptions_distinguish_fixed_and_user_selected_rates():
    minimum_content, _ = _update_dashboard(pillar2_mode="minimum")
    minimum_text = " ".join(
        component.children
        for component in minimum_content[0]._traverse()
        if isinstance(getattr(component, "children", None), str)
    )
    assert "verwendet fest 4% pro Jahr" in minimum_text
    assert "Für einen eigenen Zinssatz wähle oben «Eigene PK-Werte»." in minimum_text

    custom_content, _ = _update_dashboard(
        pillar2_mode="custom",
        pillar2_employee=100,
        pillar2_employer=200,
        pillar2_return=2.5,
    )
    custom_text = " ".join(
        component.children
        for component in custom_content[0]._traverse()
        if isinstance(getattr(component, "children", None), str)
    )
    assert "deinem gewählten Satz von 2.50% pro Jahr" in custom_text


@pytest.mark.parametrize(
    ("employee", "employer", "annual_return"),
    [
        (-1, 200, 1),
        (100, -1, 1),
        (100, 200, 20.1),
    ],
)
def test_custom_pillar2_rejects_invalid_values(employee, employer, annual_return):
    result, notice = _update_dashboard(
        pillar2_mode="custom",
        pillar2_employee=employee,
        pillar2_employer=employer,
        pillar2_return=annual_return,
    )

    assert result.__class__.__name__ == "Div"
    assert "mindestens 0 CHF" in result.children[1].children or "zwischen 0 und 20" in result.children[1].children
    assert notice == ""


@pytest.mark.parametrize(
    ("mode", "expected_rate_display", "expected_amount_display"),
    [
        ("rate", "block", "none"),
        ("amount", "none", "block"),
    ],
)
def test_3a_contribution_mode_shows_only_matching_input(
    mode, expected_rate_display, expected_amount_display
):
    rate_style, amount_style = update_savings_controls(mode)

    assert rate_style["display"] == expected_rate_display
    assert amount_style["display"] == expected_amount_display


@pytest.mark.parametrize("height", [300, 390])
def test_chart_card_sets_explicit_graph_height(height):
    card = _chart_card("Chart", "Description", None, height=height)
    graph = next(component for component in card._traverse() if component.__class__.__name__ == "Graph")

    assert graph.style["height"] == f"{height}px"
