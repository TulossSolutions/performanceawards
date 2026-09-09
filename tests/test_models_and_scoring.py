from datetime import date
from decimal import Decimal
import json
import pytest
from django.core.exceptions import ValidationError
from apps.football.models import PlayerFixture, Season
from apps.scoring.services.calculate import average_percentiles
from apps.scoring.services.context import league_factor, match_context, opponent_factor, stage_factor
from apps.scoring.services.elo import expected
from apps.scoring.services.formulas import validate_formula

pytestmark = pytest.mark.django_db

def test_season_thresholds_clamp():
    season = Season(name="2026/27", slug="x", starts_on=date(2026, 8, 1), ends_on=date(2027, 5, 31))
    assert season.progress(date(2020, 1, 1)) == 0
    assert season.progress(date(2030, 1, 1)) == 1
    assert season.eligibility_minutes(season.ends_on) == 1800
    assert season.availability_target_minutes(season.ends_on) == 2700

def test_fixture_minutes_validation():
    with pytest.raises(ValidationError): PlayerFixture(minutes=131).full_clean()

def test_context_clamps_and_stage():
    assert opponent_factor(1100) == Decimal("0.90")
    assert opponent_factor(1900) == Decimal("1.10")
    assert league_factor(1700, 1500) == Decimal("1.05")
    assert stage_factor("Final") == Decimal("1.10")
    assert Decimal("0.85") <= match_context(1100, .95, 1) <= Decimal("1.20")

def test_home_advantage_changes_expectation(): assert expected(Decimal(1500), Decimal(1500), True) > Decimal("0.5")

def test_average_tie_percentiles_are_deterministic():
    result = average_percentiles({2: Decimal(1), 1: Decimal(1), 3: Decimal(2)})
    assert result[1] == result[2] == Decimal("25")
    assert result[3] == Decimal("100")

def test_formula_weights_validate():
    with open("scoring_formulas/v1.json", encoding="utf8") as handle: config = json.load(handle)
    assert len(validate_formula(config)) == 64
    config["positions"]["FWD"]["metrics"][0]["weight"] = .31
    with pytest.raises(ValueError): validate_formula(config)
