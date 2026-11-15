"""Wohneigentumsförderung: withdrawals from the 2nd pillar and 3a (issue #26)."""

import math

import pytest

from personal_finance import config
from personal_finance.core.wef import (
    WithdrawalLimit,
    check_amount,
    latest_pillar2_age,
    pillar2_limit,
    pillar3a_limit,
)

PK = "aus der Pensionskasse"


class TestPillar2Age50Rule:
    def test_age_49_whole_balance(self):
        limit = pillar2_limit(300_000, 49, 65, balance_at_50=None)

        assert limit.maximum == 300_000
        assert limit.reasons == ()

    def test_age_50_balance_at_50_is_the_current_balance(self):
        assert pillar2_limit(300_000, 50, 65, balance_at_50=300_000).maximum == 300_000

    def test_age_51_balance_at_50_when_higher_than_half(self):
        limit = pillar2_limit(300_000, 51, 65, balance_at_50=280_000)

        assert limit.maximum == 280_000
        assert "Guthaben im Alter 50 (CHF 280’000)" in limit.reasons[0]

    def test_age_51_half_when_higher_than_balance_at_50(self):
        # E.g. after a big buy-in after 50: half of today's balance is more.
        assert pillar2_limit(300_000, 51, 65, balance_at_50=100_000).maximum == 150_000

    def test_balance_at_50_above_the_balance_is_capped(self):
        limit = pillar2_limit(200_000, 55, 65, balance_at_50=250_000)

        assert limit.maximum == 200_000
        assert limit.reasons == ()

    def test_unknown_balance_at_50_uses_half_cautiously(self):
        limit = pillar2_limit(300_000, 55, 65)

        assert limit.maximum == 150_000
        assert "Pensionskassenausweis" in limit.reasons[0]


class TestPillar2MinimumAndDeadline:
    def test_less_than_the_minimum_available_means_none(self):
        limit = pillar2_limit(19_999, 40, 65)

        assert limit.maximum == 0
        assert "mindestens CHF 20’000" in limit.reasons[0]

    def test_exactly_the_minimum_is_possible(self):
        assert pillar2_limit(config.WEF_PILLAR2_MIN_AMOUNT, 40, 65).maximum == 20_000

    def test_half_rule_can_fall_below_the_minimum(self):
        assert pillar2_limit(30_000, 55, 65).maximum == 0

    @pytest.mark.parametrize(("retirement_age", "latest"), [(65, 62), (70, 62), (60, 57)])
    def test_until_three_years_before_retirement(self, retirement_age, latest):
        assert latest_pillar2_age(retirement_age) == latest
        assert pillar2_limit(400_000, latest, retirement_age, 300_000).maximum > 0

        too_late = pillar2_limit(400_000, latest + 1, retirement_age, 300_000)
        assert too_late.maximum == 0
        assert f"bis Alter {latest}" in too_late.reasons[0]
        assert "Reglement" in too_late.reasons[0]

    @pytest.mark.parametrize(("years", "possible"), [(4, False), (5, True), (None, True)])
    def test_only_every_five_years(self, years, possible):
        limit = pillar2_limit(100_000, 40, 65, years_since_last_withdrawal=years)

        assert (limit.maximum > 0) is possible


class TestPillar3a:
    def test_whole_balance_without_minimum(self):
        assert pillar3a_limit(12_345) == WithdrawalLimit(12_345, 12_345, 0, ())

    def test_only_every_five_years(self):
        limit = pillar3a_limit(50_000, years_since_last_withdrawal=2)

        assert limit.maximum == 0
        assert "alle 5 Jahre" in limit.reasons[0]


class TestCheckAmount:
    def test_zero_is_always_fine(self):
        assert check_amount(0, pillar2_limit(0, 63, 65), PK) == 0

    def test_amount_within_the_limit(self):
        assert check_amount(50_000, pillar2_limit(100_000, 40, 65), PK) == 50_000

    def test_more_than_the_maximum(self):
        with pytest.raises(
            ValueError,
            match=r"Aus der Pensionskasse sind .* höchstens "
            r"CHF 150’000 möglich \(Guthaben voraussichtlich "
            r"CHF 300’000\)\. Ab 50",
        ):
            check_amount(200_000, pillar2_limit(300_000, 55, 65), PK)

    def test_below_the_minimum(self):
        with pytest.raises(ValueError, match="mindestens CHF 20’000"):
            check_amount(10_000, pillar2_limit(100_000, 40, 65), PK)

    def test_not_possible_names_the_reason(self):
        with pytest.raises(ValueError, match="nicht möglich. Ein Vorbezug ist nur bis"):
            check_amount(50_000, pillar2_limit(300_000, 63, 65), PK)

    def test_empty_3a_says_so(self):
        with pytest.raises(
            ValueError,
            match="Säule 3a ist .* nicht möglich. Das Guthaben beträgt voraussichtlich CHF 0",
        ):
            check_amount(1, pillar3a_limit(0), "aus der Säule 3a")

    @pytest.mark.parametrize("amount", [-1, math.nan, None, "10", True])
    def test_invalid_amounts(self, amount):
        with pytest.raises(ValueError, match="mindestens 0 CHF"):
            check_amount(amount, pillar3a_limit(10), "aus der Säule 3a")


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ((-1, 40, 65), "Pensionskassenguthaben"),
        ((100, 40.5, 65), "Alter beim Vorbezug"),
        ((100, 40, "65"), "Pensionierungsalter"),
        ((100, 55, 65, -1), "Guthaben im Alter 50"),
    ],
)
def test_invalid_pillar2_inputs(arguments, message):
    with pytest.raises(ValueError, match=message):
        pillar2_limit(*arguments)


def test_invalid_3a_balance():
    with pytest.raises(ValueError, match="3a-Guthaben"):
        pillar3a_limit(math.inf)
