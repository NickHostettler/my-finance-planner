"""Tests for Swiss salary deductions (AHV/IV/EO, ALV, NBU)."""

import pytest

from personal_finance import config
from personal_finance.core.deductions import DeductionsCalculator

MONTHLY_CAP = 148200 / 12  # CHF 12'350


def _deductions(gross_monthly, **kwargs):
    kwargs.setdefault("avg_health_insurance", 0)
    return DeductionsCalculator(gross_monthly_income=gross_monthly, **kwargs).calculate()


class TestOfficialRates:
    """Guard the statutory values against accidental edits."""

    def test_ahv_iv_eo_total_is_10_6_percent_split_evenly(self):
        assert config.AHV_IV_EO_RATE == pytest.approx(0.053)
        assert config.AHV_IV_EO_RATE + config.AHV_IV_EO_RATE_EMPLOYER == pytest.approx(0.106)

    def test_alv_total_is_2_2_percent_up_to_148200(self):
        assert config.ALV_RATE + config.ALV_RATE_EMPLOYER == pytest.approx(0.022)
        assert config.ALV_MAX_INSURED_ANNUAL_SALARY == 148200

    def test_abolished_alv_solidarity_contribution_is_gone(self):
        assert not hasattr(config, "ALV_ZUSATZ_RATE")


class TestBelowCap:
    def test_social_contributions_on_full_salary(self):
        result = _deductions(5000)

        assert result.ahv_iv_eo == pytest.approx(265.0)  # 5.3 %
        assert result.alv == pytest.approx(55.0)  # 1.1 %
        assert result.nbu == pytest.approx(5000 * config.NBU_RATE)

    def test_employer_shares(self):
        result = _deductions(5000)

        assert result.employer_ahv_iv_eo == pytest.approx(265.0)
        assert result.employer_alv == pytest.approx(55.0)


class TestAboveCap:
    def test_alv_and_nbu_are_capped_at_maximum_insured_salary(self):
        result = _deductions(20000)  # CHF 240'000 per year

        assert result.alv == pytest.approx(MONTHLY_CAP * 0.011)  # CHF 135.85
        assert result.employer_alv == pytest.approx(MONTHLY_CAP * 0.011)
        assert result.nbu == pytest.approx(MONTHLY_CAP * config.NBU_RATE)

    def test_ahv_iv_eo_has_no_cap(self):
        assert _deductions(20000).ahv_iv_eo == pytest.approx(1060.0)

    def test_regression_no_alv_on_salary_above_cap(self):
        """Old model charged 1.1 % + 0.5 % 'ALV-Zusatz' on the full salary."""
        at_cap = _deductions(MONTHLY_CAP)
        above_cap = _deductions(200000 / 12)

        assert above_cap.alv == pytest.approx(at_cap.alv)

    @pytest.mark.parametrize("gross", [MONTHLY_CAP - 1, MONTHLY_CAP, MONTHLY_CAP + 1])
    def test_alv_is_continuous_around_cap(self, gross):
        assert _deductions(gross).alv == pytest.approx(min(gross, MONTHLY_CAP) * 0.011)


class TestTotals:
    @pytest.mark.parametrize("gross", [0, 3000, 8000, MONTHLY_CAP, 25000])
    def test_net_equals_gross_minus_sum_of_all_deductions(self, gross):
        result = _deductions(gross, employee_pillar2_contribution=300, avg_health_insurance=350)
        parts = (
            result.ahv_iv_eo
            + result.alv
            + result.nbu
            + result.krankenkasse
            + result.pensionskasse
            + result.income_tax
        )

        assert result.total_employee_deductions == pytest.approx(parts)
        assert result.net_monthly_income == pytest.approx(gross - parts)

    def test_net_income_rises_monotonically_across_the_cap(self):
        salaries = [10000, 12000, MONTHLY_CAP, 13000, 15000, 20000]
        nets = [_deductions(s).net_monthly_income for s in salaries]

        assert nets == sorted(nets)

    def test_no_income_tax_below_allowance(self):
        assert _deductions(config.ANNUAL_TAX_ALLOWANCE / 12).income_tax == 0

    def test_summary_lists_all_deductions_and_handles_zero_income(self):
        summary = DeductionsCalculator(gross_monthly_income=0).get_summary()

        assert set(summary["deductions"]) == {
            "ahv_iv_eo", "alv", "nbu", "krankenkasse", "pensionskasse", "income_tax",
        }
        assert summary["net_rate"] == 0.0
