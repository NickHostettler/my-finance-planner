"""Life phases in the results: the "Lebensphasen" tab and the other tabs (issue #33)."""

from types import SimpleNamespace

import pytest

from personal_finance.core.income import normalize_income
from personal_finance.dashboard import callbacks, life_view
from personal_finance.dashboard.components import money
from personal_finance.dashboard.figures import phases_figure
from tests.ui.test_callbacks import HOME, metric_values, results, texts

# Net 7'200 a month today at 35: full time until 37, 60 % until 44, then 80 %; two children.
LIFE = {
    "life_plan": "on",
    "life_1_to": 37,
    "life_1_workload": 100,
    "life_1_income": 7_200,
    "life_2_to": 44,
    "life_2_workload": 60,
    "life_2_income": 4_300,
    "life_2_costs": 1_500,
    "life_3_workload": 80,
    "life_3_income": 5_800,
    "life_3_costs": 600,
    "life_child_1": 36,
    "life_child_2": 39,
}
FULL_TIME = {"life_plan": "on", "life_1_workload": 100, "life_1_income": 7_200}


def tabs(**overrides):
    overview, pension, home, life, assumptions, notice = results(**{**LIFE, **overrides})
    return SimpleNamespace(
        overview=overview, pension=pension, home=home, life=life, assumptions=assumptions
    )


def total(overview) -> str:
    return metric_values(overview)[0]  # "Projiziertes Vorsorgekapital"


class TestLifeTab:
    def test_shows_the_gap_charts_phases_and_family(self):
        life = tabs().life
        text = texts(life)

        assert "Vorsorgelücke bei Pensionierung" in text
        assert "AHV-Lücke pro Monat" in text
        assert "Angaben fehlen" in text  # no AHV inputs
        graphs = [node for node in life._traverse() if type(node).__name__ == "Graph"]
        assert len(graphs) == 2
        rows = [node for node in life._traverse() if type(node).__name__ == "TableTr"]
        assert len(rows) == 1 + 3  # header and three phases
        assert "35–37" in text and "38–44" in text and "45–64" in text
        assert "Familienzulagen bis zur Pensionierung" in text
        assert "Kinderkosten bis zur Pensionierung" in text

    def test_gap_is_positive_with_part_time(self):
        gap = metric_values(tabs().life)[0]

        assert gap.startswith("CHF ")
        assert float(gap[4:].replace("’", "")) > 0

    def test_ahv_with_the_education_credits(self):
        life = tabs(ahv_average_income=70_000).life
        text = texts(life)

        assert "inkl. Erziehungsgutschriften" in text
        assert "Jahre mit AHV-Erziehungsgutschrift" in text
        assert metric_values(life)[1] != "Angaben fehlen"

    def test_real_values_are_lower(self):
        nominal = metric_values(tabs().life)[0]
        real = metric_values(tabs(display_basis="real").life)[0]

        assert float(real[4:].replace("’", "")) < float(nominal[4:].replace("’", ""))

    def test_hint_without_life_phases(self):
        assert "Lebensphasen planen" in texts(tabs(life_plan="off").life)

    def test_invalid_phases_only_in_their_tab(self):
        broken = tabs(life_1_to=None)
        without = tabs(life_plan="off")

        assert "Lebensphasen: Eingaben prüfen" in texts(broken.life)
        assert "Phase 1: Bitte gib an, bis zu welchem Alter" in texts(broken.life)
        assert total(broken.overview) == total(without.overview)


def test_assumptions_explain_life_phases_and_family_with_sources():
    text = texts(tabs(life_plan="off").assumptions)

    assert "Lebensphasen · Teilzeit und Unterbrüche" in text
    assert "CHF 23’040" in text and "CHF 26’880" in text
    assert "höchstens CHF 36’864" in text
    assert "Erziehungsgutschrift von CHF 46’080" in text
    assert "Familie · Zulagen und Erwerbsersatz" in text
    assert "Kinderzulage mindestens CHF 215" in text
    assert "höchstens CHF 220 pro Tag" in text
    assert "Erwerbsersatz bei Elternschaft (BSV)" in text


class TestOtherTabs:
    def test_overview_counts_the_phases(self):
        with_phases = tabs()
        without = tabs(life_plan="off")

        assert "Mit deinen Lebensphasen gerechnet" in texts(with_phases.overview)
        assert "weniger Vorsorgekapital" in texts(with_phases.overview)
        assert total(with_phases.overview) != total(without.overview)

    def test_one_full_time_phase_gives_the_same_projection(self):
        assert total(tabs(**FULL_TIME, life_2_workload=None, life_3_workload=None).overview) == (
            total(tabs(life_plan="off").overview)
        )

    def test_more_income_gives_more_capital(self):
        overview = tabs(life_3_income=9_000, life_2_workload=None, life_3_workload=None).overview
        # Only one row is used: the first phase with 7'200 until retirement.
        assert "Mit deinen Lebensphasen" in texts(overview)
        richer = tabs(life_1_income=9_000, life_2_workload=None, life_3_workload=None).overview
        assert "mehr Vorsorgekapital" in texts(richer)

    def test_overview_ahv_follows_the_phases(self):
        with_phases = tabs(ahv_average_income=70_000).overview
        without = tabs(ahv_average_income=70_000, life_plan="off").overview

        assert metric_values(with_phases)[-1] != metric_values(without)[-1]

    def test_home_purchase_with_life_phases(self):
        result = tabs(**HOME)

        assert "Ampel:" in texts(result.home)
        assert "Mit dem geplanten Kauf" in texts(result.overview)
        assert "Mit deinen Lebensphasen gerechnet" in texts(result.overview)


class TestHints:
    def test_costs_higher_than_the_income(self):
        text = texts(tabs(life_2_costs=6_000).life)

        assert "Ausgaben höher als das Einkommen" in text
        assert "Mit 38–44 reichen Einkommen und Zulagen nicht" in text

    def test_tips_for_the_pension_fund(self):
        fixed = texts(tabs().life)
        by_workload = texts(tabs(life_coordination="workload").life)

        assert "Einkauf in die Pensionskasse" in fixed
        assert "Koordinationsabzug ans Pensum anpasst" in fixed
        assert "Koordinationsabzug ans Pensum anpasst" not in by_workload
        assert "an dein Pensum angepasst" in by_workload

    def test_large_3a_without_pension_fund(self):
        # 1'500 a month = 18'000 a year: below the entry threshold.
        text = texts(tabs(life_2_income=1_500, life_2_workload=20).life)

        assert "höchstens CHF 36’864" in text

    def test_break_without_income(self):
        text = texts(tabs(life_2_workload=0, life_2_income=0).life)

        assert "Ohne Erwerb (mit 38–44)" in text

    def test_no_tips_without_a_gap(self):
        text = texts(tabs(**FULL_TIME, life_2_workload=None, life_3_workload=None).life)

        assert "Hinweise, keine Beratung" not in text

    def test_age_ranges(self):
        assert life_view.age_ranges([34, 35, 36, 40]) == "34–36, 40"


class TestIncomeBasis:
    def test_gross_phase_incomes_are_turned_into_net(self):
        life = tabs(income_type="gross", income=9_000, life_1_income=9_000).life
        net = normalize_income(9_000, "monthly", "gross", 35, "ZH")[0]

        assert money(net) in texts(life)

    def test_own_pension_fund_contributions(self):
        text = texts(
            tabs(
                pillar2_mode="custom", pillar2_employee=400, pillar2_employer=500, pillar2_return=2
            ).life
        )

        assert "eigene Werte" in text

    @pytest.mark.parametrize(
        ("income_type", "amount", "expected"),
        [
            ("net", 5_000, 5_000),
            ("gross", None, None),
            ("gross", 0, 0),
            ("gross", True, True),
            ("gross", float("nan"), "nan"),
        ],
    )
    def test_to_net_leaves_what_it_cannot_convert(self, income_type, amount, expected):
        base = SimpleNamespace(values={"income_type": income_type, "canton": "ZH"}, current_age=35)
        result = callbacks._phase_income_to_net(base)(amount)

        assert str(result) == str(expected)


class TestEdgeCases:
    def test_at_retirement_there_are_no_years(self):
        one_phase = {**FULL_TIME, "life_2_workload": None, "life_3_workload": None}
        life = tabs(current_age=65, retirement_age=65, **one_phase).life

        rows = [node for node in life._traverse() if type(node).__name__ == "TableTr"]
        assert len(rows) == 1  # only the header

    def test_births_outside_the_plan_have_no_marker(self):
        figure = phases_figure([35, 36], [1, 1], [7_000, 7_000], [30])
        with_birth = phases_figure([35, 36], [1, 1], [7_000, 7_000], [36])

        assert [trace.name for trace in figure.data] == ["Pensum", "Einkommen pro Monat"]
        assert with_birth.data[-1].name == "Geburt"
        assert phases_figure([], [], [], [36]).data[-1].name == "Einkommen pro Monat"
