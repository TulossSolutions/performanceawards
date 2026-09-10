from unittest.mock import Mock, patch
import httpx
import pytest
from django.test import override_settings
from apps.football.models import Position
from apps.ingestion.providers.positions import normalize_position
from apps.ingestion.providers.api_football import ApiFootballProvider
from apps.ingestion.providers.base import ProviderRequestLimitReached

def test_position_priority_and_unknown():
    assert normalize_position("goalkeeper", "ST", Position.FWD) == Position.GK
    assert normalize_position(None, "CB", None) == Position.DEF
    assert normalize_position(None, None, None) == Position.UNKNOWN
    assert normalize_position("G") == Position.GK
    assert normalize_position("D") == Position.DEF
    assert normalize_position("M") == Position.MID
    assert normalize_position("F") == Position.FWD

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
@patch("apps.ingestion.providers.api_football.time.sleep")
def test_retries_429_and_5xx(sleep):
    responses = [Mock(status_code=429, headers={}), Mock(status_code=503, headers={}), Mock(status_code=200, headers={}, json=lambda: {"response": [], "errors": []})]
    for response in responses: response.raise_for_status = Mock()
    client = Mock(); client.get.side_effect = responses
    assert ApiFootballProvider(client)._request("fixtures") == {"response": [], "errors": []}
    assert client.get.call_count == 3
    assert client.get.call_args.kwargs["headers"] == {"x-apisports-key": "secret"}

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_no_retry_on_ordinary_4xx():
    request = httpx.Request("GET", "https://example.test")
    client = Mock(); client.get.return_value = httpx.Response(404, request=request)
    with pytest.raises(httpx.HTTPStatusError): ApiFootballProvider(client)._request("missing")
    assert client.get.call_count == 1

@override_settings(API_FOOTBALL_KEY="super-secret", API_FOOTBALL_BASE_URL="https://example.test")
@patch("apps.ingestion.providers.api_football.time.sleep")
def test_token_is_not_logged_during_retry(sleep, caplog):
    request=httpx.Request("GET","https://example.test")
    client=Mock(); client.get.return_value=httpx.Response(429,request=request)
    with pytest.raises(httpx.HTTPStatusError): ApiFootballProvider(client)._request("fixtures")
    assert "super-secret" not in caplog.text

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_http_200_provider_errors_are_rejected():
    client=Mock(); client.get.return_value=Mock(status_code=200,headers={},raise_for_status=Mock(),json=lambda:{"errors":{"fixture":"invalid"},"response":[]})
    with pytest.raises(ValueError,match="response errors"): ApiFootballProvider(client)._request("fixtures")

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_free_plan_quota_stops_before_another_request():
    client=Mock(); client.get.return_value=Mock(status_code=200,headers={"x-ratelimit-requests-remaining":"0"},raise_for_status=Mock(),json=lambda:{"errors":[],"response":[]})
    provider=ApiFootballProvider(client)
    provider._request("fixtures")
    with pytest.raises(RuntimeError,match="quota exhausted"): provider._request("fixtures/players")
    assert client.get.call_count == 1

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_first_page_does_not_send_unsupported_page_parameter():
    client=Mock(); client.get.return_value=Mock(status_code=200,headers={},raise_for_status=Mock(),json=lambda:{"errors":[],"response":[],"paging":{"current":1,"total":1}})
    ApiFootballProvider(client)._all("leagues")
    assert client.get.call_args.kwargs["params"] == {}

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_non_iso3_country_code_is_not_persisted_as_iso3():
    payload={"errors":[],"response":[{"league":{"id":39,"name":"Premier League","type":"League"},"country":{"code":"GB-ENG"}}],"paging":{"current":1,"total":1}}
    client=Mock(); client.get.return_value=Mock(status_code=200,headers={},raise_for_status=Mock(),json=lambda:payload)
    assert ApiFootballProvider(client).list_competitions()[0].country_code is None

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_fixture_list_metadata_avoids_duplicate_fixture_request():
    fixture_payload={"fixture":{"id":10,"date":"2024-08-10T12:00:00+00:00","status":{"short":"FT"}},"league":{"id":39,"season":2024,"round":"Regular Season - 1"},"teams":{"home":{"id":1,"name":"Home"},"away":{"id":2,"name":"Away"}},"goals":{"home":1,"away":0}}
    players_payload={"errors":[],"response":[],"paging":{"current":1,"total":1}}
    client=Mock(); client.get.return_value=Mock(status_code=200,headers={},raise_for_status=Mock(),json=lambda:players_payload)
    provider=ApiFootballProvider(client); fixture=provider._normalize_fixture_meta(fixture_payload)
    bundle=provider.get_fixture_details(fixture)
    assert bundle.fixture.id == "10"
    assert client.get.call_count == 1
    assert client.get.call_args.kwargs["params"] == {"fixture":"10"}

@override_settings(API_FOOTBALL_KEY="secret", API_FOOTBALL_BASE_URL="https://example.test")
def test_configured_request_budget_is_a_hard_ceiling():
    response=Mock(status_code=200,headers={},raise_for_status=Mock(),json=lambda:{"errors":[],"response":[]})
    client=Mock(); client.get.return_value=response
    provider=ApiFootballProvider(client); provider.configure_request_limits(max_requests=1)
    provider._request("fixtures")
    with pytest.raises(ProviderRequestLimitReached,match="budget"):
        provider._request("fixtures/players")
    assert provider.requests_made == 1
    assert client.get.call_count == 1
