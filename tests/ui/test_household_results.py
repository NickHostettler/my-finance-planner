"""Results for two persons: personal tabs, the "Haushalt" tab and a joint purchase (v1.3).

Issues #41 (personal projections), #42 (money per person), #46 (joint affordability).
"""

from types import SimpleNamespace

import pytest

from personal_finance.dashboard import callbacks
from personal_finance.dashboard.callbacks import (
    fill_home_maximum,
    update_home_amount_hints,
    update_result_person,
)
from personal_finance.storage import browser_store
from tests.ui.test_callbacks import (
    VALID_INPUTS,
    chf,
    metric_values,
    results,
    run_callback,
    texts,
)

# Person A: 35, net 7'200 per month (VALID_INPUTS). Person B: 33, net 5'000, retires at 64.
PAIR = {
    "household": "on",
    "household_relationship": "married",
    "b_current_age": 33,
    "b_retirement_age": 64,
    "b_income": 5000,
}
# A joint purchase today: both have pension fund money and free assets.
JOINT = {
    **PAIR,
    "initial_2": 100_000,
    "initial_3b": 150_000,
    "b_initial_2": 80_000,
    "b_initial_3b": 60_000,
    "home_plan": "on",
    "home_price": 1_000_000,
    "home_savings": 150_000,
    "home_pillar3a": 0,
    "home_pillar2": 0,
    "b_home_savings": 60_000,
    "b_home_pillar3a": 0,
    "b_home_pillar2": 30_000,
    "home_gross_income": 220_000,
}


def tabs(**overrides):
    (
        overview,
        pension,
        home,
        life,
        assumptions,
        household,
        b_overview,
        b_pension,
        b_life,
        notice,
    ) = results(**overrides)
    return SimpleNamespace(**locals())


class TestPersonalResults:
    def test_one_person_has_no_results_for_person_b(self):
        result = tabs()
        assert (result.b_overview, result.b_pension, result.b_life) == ("", "", "")
        assert "Zu zweit planen" in texts(result.household)

    def test_each_person_has_own_tabs(self):
        result = tabs(**PAIR)
        assert "Person A · 35 Jahre · Pensionierung mit 65" in texts(result.overview)
        assert "Person B · 33 Jahre · Pensionierung mit 64" in texts(result.b_overview)
        assert "Person B" in texts(result.b_pension)
        assert "Lebensphasen planen" in texts(result.b_life)

    def test_person_b_does_not_change_person_a(self):
        # Acceptance (#41): changes of person B leave the projection of person A as it is.
        one = tabs(**PAIR)
        other = tabs(**{**PAIR, "b_income": 9000, "b_initial_2": 250_000, "b_current_age": 50})
        assert repr(one.overview) == repr(other.overview)
        assert repr(one.pension) == repr(other.pension)
        assert repr(one.b_overview) != repr(other.b_overview)

    def test_the_projection_of_person_b_uses_person_b(self):
        # Person A alone with the start values of person B: the same projection.
        alone = tabs(
            **{
                **VALID_INPUTS,
                **browser_store.PERSON_B_DEFAULTS,
                "current_age": 33,
                "retirement_age": 64,
            }
        )
        pair = tabs(**PAIR)
        assert metric_values(pair.b_overview) == metric_values(alone.overview)

    def test_errors_of_person_b_only_in_person_b_and_shared_tabs(self):
        result = tabs(**{**PAIR, "b_current_age": None, "home_plan": "on"})
        message = "Person B: Bitte wähle dein aktuelles Alter"
        for section in (result.b_overview, result.b_pension, result.b_life):
            assert message in texts(section)
        assert message in texts(result.home)
        assert message in texts(result.household)
        assert "Projiziertes Vorsorgekapital" in texts(result.overview)
        assert "Haushalt mit zwei Personen" in texts(result.assumptions)

    def test_errors_of_person_a_with_two_persons(self):
        result = tabs(**{**PAIR, "current_age": None})
        assert "Person A: Bitte wähle" in texts(result.overview)
        assert "Projiziertes Vorsorgekapital" in texts(result.b_overview)
        assert "Person A: Bitte wähle" in texts(result.assumptions)

    def test_invalid_household_choice(self):
        *sections, notice = results(**{**PAIR, "household_relationship": "x"})
        assert all("verheiratet" in texts(section) for section in sections)
        assert notice == ""

    def test_3a_limit_notice_names_the_person(self):
        notice = tabs(**{**PAIR, "b_pillar3a_amount": 2000}).notice
        assert notice.startswith("Person B: Der eingegebene 3a-Beitrag")

    def test_result_person_switch(self):
        shown, hidden = {"display": "block"}, {"display": "none"}
        assert update_result_person("off", "b") == [hidden] + [shown, hidden] * 3
        assert update_result_person("on", "a") == [shown] + [shown, hidden] * 3
        assert update_result_person("on", "b") == [shown] + [hidden, shown] * 3


class TestHouseholdTab:
    def test_both_persons_side_by_side(self):
        text = texts(tabs(**PAIR).household)
        assert "Persönliche Vorsorge im Vergleich" in text
        assert "Jede Person bei ihrer eigenen Pensionierung · nominal" in text
        assert "Person A" in text and "Person B" in text
        assert "Nettoeinkommen des Haushalts" in text
        assert "CHF 12’200/Monat" in text  # 7'200 + 5'000
        assert "wird nicht zusammengezählt" in text
        assert "Kein Kauf geplant" in text
        assert "Ehepaare werden gemeinsam besteuert" in text

    def test_real_values(self):
        text = texts(tabs(**{**PAIR, "display_basis": "real"}).household)
        assert "heutige Kaufkraft" in text

    def test_ahv_of_married_couples_is_capped(self):
        high = {"ahv_average_income": 92_160, "b_ahv_average_income": 92_160}
        married = tabs(**{**PAIR, **high})
        # 2 x 2'560 = 5'120 > 3'840: both pensions times 0.75 (1'920 today).
        assert "Plafoniert: Ehepaare erhalten zusammen höchstens CHF 3’840" in texts(
            married.household
        )
        assert "CHF 3’840/Monat" in texts(married.household)
        assert "plafoniert (Ehepaar)" in texts(married.overview)
        unmarried = tabs(**{**PAIR, **high, "household_relationship": "unmarried"})
        assert "keine Plafonierung" in texts(unmarried.household)
        assert "CHF 5’120/Monat" in texts(unmarried.household)
        assert "Ohne Ehe gibt es keine Witwen" in texts(unmarried.household)

    def test_married_below_the_cap(self):
        text = texts(
            tabs(**{**PAIR, "ahv_average_income": 30_000, "b_ahv_average_income": 30_000}).household
        )
        assert "Unter der Plafonierung für Ehepaare" in text

    def test_ahv_missing(self):
        text = texts(tabs(**{**PAIR, "ahv_average_income": None}).household)
        assert "Für beide unter «AHV-Rente» das Einkommen angeben" in text

    def test_purchase_with_an_error(self):
        text = texts(tabs(**{**JOINT, "home_price": None}).household)
        assert "Eingaben prüfen" in text

    def test_household_assumptions(self):
        assert "Haushalt mit zwei Personen" in texts(tabs(**PAIR).assumptions)
        assert "Haushalt mit zwei Personen" not in texts(tabs().assumptions)


class TestJointPurchase:
    def test_affordability_with_both_incomes_and_money(self):
        result = tabs(**JOINT)
        text = texts(result.home)
        assert "Kauf heute (Person A 35, Person B 33)" in text
        assert "Kaufmittel je Person" in text
        # Savings 150'000 + 60'000, PK 30'000 from person B: 240'000 together.
        assert "CHF 240’000" in text
        assert "Vorsorgegeld von Person A für den Kauf (WEF)" in text
        assert "Vorsorgegeld von Person B für den Kauf (WEF)" in text
        assert "Hypothek bei der ersten Pensionierung" in text
        assert "Hypothek und Vermögen bis zur ersten Pensionierung" in text
        assert "Wenn beide pensioniert sind" in text
        assert "Höchster Kaufpreis zum Kaufzeitpunkt" in text
        household = texts(result.household)
        assert "Kaufmittel je Person" in household
        assert "Kauf heute (Person A 35, Person B 33)" in household

    def test_a_withdrawal_lowers_only_the_own_projection(self):
        without = tabs(**PAIR)
        joint = tabs(**{**JOINT, "b_home_pillar2": 30_000})
        no_pension_money = tabs(**{**JOINT, "b_home_pillar2": 0, "b_home_savings": 90_000})
        assert "Vorbezug Pensionskasse CHF 30’000" in texts(joint.b_overview)
        assert "Vorbezug Pensionskasse" not in texts(joint.overview)
        # Person B's pension fund at retirement is lower with the withdrawal.
        assert metric_values(joint.b_overview)[1] != metric_values(no_pension_money.b_overview)[1]
        assert "gemeinsamen Kauf" in texts(joint.b_overview)
        assert without.home is not None

    def test_amounts_are_checked_for_their_person(self):
        text = texts(tabs(**{**JOINT, "b_home_pillar2": 500_000}).home)
        assert "Aus der Pensionskasse von Person B sind zum Kaufzeitpunkt höchstens" in text

    def test_a_net_income_in_the_household(self):
        text = texts(tabs(**{**JOINT, "home_gross_income": None}).home)
        assert "Mindestens eine Person hat ein Nettoeinkommen angegeben" in text

    def test_missing_ahv_for_the_check_in_retirement(self):
        text = texts(tabs(**{**JOINT, "ahv_average_income": None}).home)
        assert "Für die AHV gebt bei beiden Personen" in text

    def test_buy_before_the_first_retirement(self):
        # Person B retires at 60 in 27 years: person A (35) buys at 61 at the latest.
        early = {**JOINT, "b_retirement_age": 60, "b_home_pillar2": 0, "home_purchase_age": 62}
        text = texts(tabs(**early).home)
        assert "Das Kaufalter von Person A muss eine ganze Zahl zwischen 35 und 61 sein" in text
        assert "ersten Pensionierung im Haushalt" in text

    def test_indirect_amortisation_shares_the_3a_room(self):
        text = texts(
            tabs(
                **{
                    **JOINT,
                    "home_amortisation": "indirect",
                    "pillar3a_amount": callbacks.PILLAR3A_MAX_MONTHLY_INPUT,
                    "b_pillar3a_amount": callbacks.PILLAR3A_MAX_MONTHLY_INPUT,
                }
            ).home
        )
        assert "neben euren 3a-Plänen" in text


class TestLifePhasesOfBoth:
    LIFE_B = {
        "b_life_plan": "on",
        "b_life_1_workload": 100,
        "b_life_1_income": 5000,
        "life_child_1": 37,  # person A is 37 at the birth, person B 35
    }

    def test_children_count_for_person_b_with_the_age_difference(self):
        text = texts(tabs(**{**PAIR, **self.LIFE_B}).b_life)
        assert "Vorsorgelücke bei Pensionierung" in text
        assert "Jahre mit AHV-Erziehungsgutschrift" in text

    def test_allowances_count_once(self):
        both = {
            **PAIR,
            **self.LIFE_B,
            "life_plan": "on",
            "life_1_workload": 100,
            "life_1_income": 7200,
        }
        result = tabs(**both)
        assert "Die Familienzulagen sind bei Person A gerechnet." in texts(result.b_life)
        assert "Die Familienzulagen sind bei" not in texts(result.life)
        assert "Vorsorgelücke durch Lebensphasen" in texts(result.household)

    def test_only_person_b_plans_life_phases(self):
        result = tabs(**{**PAIR, **self.LIFE_B})
        assert "Die Familienzulagen sind bei" not in texts(result.b_life)

    def test_a_child_before_person_b_was_born(self):
        text = texts(
            tabs(**{**PAIR, **self.LIFE_B, "b_current_age": 20, "life_child_1": 10}).b_life
        )
        assert "Kind 1: Person B wäre bei der Geburt noch nicht geboren" in text

    @pytest.mark.parametrize(
        ("relationship", "expected"),
        [
            ("married", "bist du in der AHV gedeckt, wenn die andere Person"),
            ("unmarried", "Ohne Ehe deckt dich die andere Person nicht"),
        ],
    )
    def test_ahv_hints_without_income(self, relationship, expected):
        breaks = {
            **PAIR,
            "household_relationship": relationship,
            "b_life_plan": "on",
            "b_life_1_to": 35,
            "b_life_1_workload": 100,
            "b_life_1_income": 5000,
            "b_life_2_to": 37,
            "b_life_2_workload": 0,
            "b_life_2_income": 0,
            "b_life_3_workload": 100,
            "b_life_3_income": 5000,
        }
        assert expected in texts(tabs(**breaks).b_life)

    def test_unmarried_credits_in_full_for_one_person(self):
        base = {
            **PAIR,
            **self.LIFE_B,
            "household_relationship": "unmarried",
            "ahv_average_income": 60_000,
            "b_ahv_average_income": 60_000,
        }
        to_b = tabs(**{**base, "household_credits": "b"})
        to_a = tabs(**{**base, "household_credits": "a"})
        # Person B gets all the credits or none: the AHV of person B differs (5th card).
        assert chf(metric_values(to_b.b_overview)[4]) > chf(metric_values(to_a.b_overview)[4])


class TestPrefill:
    def components(self, **overrides):
        values = browser_store.values_to_inputs({**VALID_INPUTS, **JOINT, **overrides})
        return dict(zip(callbacks.SCENARIO_INPUT_IDS, callbacks._to_components(values)))

    def test_both_persons_get_their_highest_amounts(self):
        fields = self.components()
        others = [fields[component_id] for component_id in callbacks._PREFILL_STATE_IDS]
        result = run_callback("home-plan-input", fill_home_maximum, "on", None, 1, None, *others)
        # Free assets 150'000 + 60'000, no 3a; the pension funds fill up the rest.
        assert result[0] == 150_000 and result[3] == 60_000
        assert result[1] == result[4] == 0
        assert result[2] == 100_000  # all of person A's pension fund
        assert result[5] == 80_000
        assert result[-1] is None

    def test_hints_for_person_b(self):
        fields = self.components()
        hints = update_home_amount_hints(
            *[fields[component_id] for component_id in callbacks._HINT_INPUT_IDS]
        )
        assert hints[3].startswith("Freies Vermögen zum Kaufalter: CHF 60’000")
        assert hints[5].startswith("Höchstens CHF 80’000 zum Kaufalter")

    def test_no_hints_while_a_person_is_invalid(self):
        fields = self.components(b_current_age=None)
        hints = update_home_amount_hints(
            *[fields[component_id] for component_id in callbacks._HINT_INPUT_IDS]
        )
        assert hints[0] == "Inkl. Geld für die Kaufnebenkosten"

    def test_amounts_with_life_phases(self):
        # The highest amounts follow the projection with the life phases of person B.
        life = {"b_life_plan": "on", "b_life_1_workload": 100, "b_life_1_income": 5000}
        fields = self.components(**life, home_purchase_age=45)
        hints = update_home_amount_hints(
            *[fields[component_id] for component_id in callbacks._HINT_INPUT_IDS]
        )
        assert hints[3].startswith("Freies Vermögen zum Kaufalter: CHF ")
        assert hints[3] != self.hints_without_life()[3]

    def hints_without_life(self):
        fields = self.components(home_purchase_age=45, b_pillar3b_amount=0)
        return update_home_amount_hints(
            *[fields[component_id] for component_id in callbacks._HINT_INPUT_IDS]
        )
