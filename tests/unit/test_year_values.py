"""The yearly values belong to the same year and follow from each other (issue #29).

BVG limits and the 3a maximum are derived from the maximum AHV pension. If only some of
them are updated for a new year, these tests fail.
"""

from personal_finance import config
from personal_finance.core import ahv

# Maximum AHV old-age pension per year: 2'560 x 12 = 30'720 (from 1.1.2027).
MAX_PENSION_YEAR = ahv.MAXIMUM_FULL_MONTHLY_PENSION * 12


def test_values_valid_from_2027():
    assert (ahv.MINIMUM_FULL_MONTHLY_PENSION, ahv.MAXIMUM_FULL_MONTHLY_PENSION) == (1280, 2560)
    assert (ahv.MINIMUM_PENSION_INCOME, ahv.MAXIMUM_PENSION_INCOME) == (15_360, 92_160)
    assert config.PILLAR2_MIN_SALARY == 23_040
    assert config.PILLAR2_COORDINATION_DEDUCTION == 26_880
    assert config.PILLAR3A_ANNUAL_MAX == 7_373


def test_bvg_limits_follow_from_the_maximum_ahv_pension():
    # BVG Art. 2 / 7 / 8: entry threshold 3/4, coordination deduction 7/8, upper limit 3x,
    # minimum coordinated salary 1/8 of the maximum yearly AHV pension.
    assert config.PILLAR2_MIN_SALARY == MAX_PENSION_YEAR * 3 / 4
    assert config.PILLAR2_COORDINATION_DEDUCTION == MAX_PENSION_YEAR * 7 / 8
    assert config.PILLAR2_MAX_SALARY == MAX_PENSION_YEAR * 3
    assert config.PILLAR2_MIN_COORDINATED_SALARY == MAX_PENSION_YEAR / 8
    assert config.PILLAR2_MAX_COORDINATED_SALARY == 65_280


def test_3a_maximum_is_8_percent_of_the_bvg_upper_limit():
    # 8 % x 92'160 = 7'372.80, rounded to 7'373.
    assert config.PILLAR3A_ANNUAL_MAX == round(config.PILLAR2_MAX_SALARY * 0.08)


def test_ahv_scale_matches_the_bvg_upper_limit():
    assert ahv.MAXIMUM_PENSION_INCOME == config.PILLAR2_MAX_SALARY
