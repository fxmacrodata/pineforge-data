from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from pineforge_data import (
    FxMacroDataAccessWarning,
    FxMacroDataDataError,
    FxMacroDataHTTPError,
    FxMacroDataProvider,
    FxMacroDataResponse,
    MacroDataProvider,
    MacroObservation,
    MacroRequest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "fxmacrodata_usd_non_farm_payrolls.json"
START_MS = 1_775_001_600_000  # 2026-04-01
END_MS = 1_790_812_800_000  # 2026-10-01


def fixture_pages() -> list[object]:
    pages: list[object] = json.loads(FIXTURE.read_text(encoding="utf-8"))["pages"]
    return pages


class FakeTransport:
    def __init__(self, responses: list[FxMacroDataResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict[str, str | int], dict[str, str]]] = []

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        headers: Mapping[str, str],
    ) -> FxMacroDataResponse:
        self.calls.append((url, dict(params), dict(headers)))
        return self._responses.pop(0)


def ok(payload: object) -> FxMacroDataResponse:
    return FxMacroDataResponse(200, payload)


def fetch(
    provider: FxMacroDataProvider, start_ms: int = START_MS, end_ms: int = END_MS
) -> list[MacroObservation]:
    request = MacroRequest(
        key="non_farm_payrolls", currency="usd", start_ms=start_ms, end_ms=end_ms
    )
    return list(asyncio.run(provider.fetch_observations(request)))


def test_provider_implements_macro_protocol() -> None:
    assert isinstance(FxMacroDataProvider(transport=FakeTransport([])), MacroDataProvider)


def test_fixture_pages_become_release_and_vintage_observations() -> None:
    transport = FakeTransport([ok(page) for page in fixture_pages()])
    provider = FxMacroDataProvider(transport=transport)

    observations = fetch(provider)

    assert [
        (o.period_end_ms, o.released_at_ms, o.vintage_at_ms, o.value) for o in observations
    ] == [
        # June: no revisions, one vintage at the release time
        (1_782_777_600_000, 1_783_513_800_000, 1_783_513_800_000, 158_936_000.0),
        # July: first print at release, the revised value only from when it was observed
        (1_785_456_000_000, 1_786_105_800_000, 1_786_105_800_000, 158_858_000.0),
        (1_785_456_000_000, 1_786_105_800_000, 1_789_364_950_289, 158_913_000.0),
        # August: the snapshot repeats the first print, so it adds no vintage
        (1_788_134_400_000, 1_788_525_000_000, 1_788_525_000_000, 159_075_000.0),
    ]
    assert {(o.key, o.currency, o.unit, o.source) for o in observations} == {
        ("non_farm_payrolls", "USD", "Persons", "BLS")
    }
    assert provider.last_skipped == {"unknown_release_time": 1, "assumed_release_time": 1}

    first_url, first_params, _ = transport.calls[0]
    assert first_url == "https://api.fxmacrodata.com/v1/announcements/USD/non_farm_payrolls"
    assert first_params == {
        "start_date": "2026-04-01",
        "end_date": "2026-09-30",
        "limit": 100,
        "offset": 0,
        "revisions": "all",
    }
    assert transport.calls[1][1]["offset"] == 2


def test_missing_release_time_is_never_fabricated() -> None:
    page = {
        "data": [
            {
                "date": "2026-05-31",
                "val": 1.0,
                "announcement_datetime": None,
                "official_planned_release_datetime": 1_780_000_000,
                "publication_time_status": "unknown",
            }
        ]
    }
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    assert fetch(provider) == []
    assert provider.last_skipped == {"unknown_release_time": 1}


def test_assumed_release_times_are_opt_in() -> None:
    pages = fixture_pages()
    provider = FxMacroDataProvider(
        include_assumed_release_times=True,
        transport=FakeTransport([ok(page) for page in pages]),
    )

    observations = fetch(provider)

    assert (1_777_507_200_000, 1_778_247_000_000, 158_700_000.0) in {
        (o.period_end_ms, o.released_at_ms, o.value) for o in observations
    }
    assert provider.last_skipped == {"unknown_release_time": 1}


def test_snapshot_without_observation_time_is_skipped() -> None:
    page = {
        "data": [
            {
                "date": "2026-07-31",
                "val": 2.0,
                "announcement_datetime": 1_786_105_800,
                "revisions": [
                    {"epoch": 1_786_105_800, "val": 1.0, "vintage_status": "source_vintage"},
                    {"epoch": 1_786_105_800, "val": 2.0, "vintage_status": "captured_snapshot"},
                ],
            }
        ]
    }
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    assert [o.value for o in fetch(provider)] == [1.0]
    assert provider.last_skipped == {"revision_without_vintage_time": 1}


def test_release_before_period_end_is_skipped_not_reordered() -> None:
    page = {"data": [{"date": "2026-07-31", "val": 50.1, "announcement_datetime": 1_785_000_000}]}
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    assert fetch(provider) == []
    assert provider.last_skipped == {"released_before_period_end": 1}


def test_periods_outside_the_request_are_dropped() -> None:
    pages = fixture_pages()
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page) for page in pages]))

    observations = fetch(provider, start_ms=1_785_456_000_000, end_ms=1_788_134_400_000)

    assert {o.period_end_ms for o in observations} == {1_785_456_000_000}


def test_api_key_is_sent_only_in_header() -> None:
    transport = FakeTransport([ok({"data": []})])
    provider = FxMacroDataProvider(api_key="placeholder-key", transport=transport)

    fetch(provider)

    url, params, headers = transport.calls[0]
    assert headers["X-API-Key"] == "placeholder-key"
    assert "placeholder-key" not in url
    assert "placeholder-key" not in json.dumps(params)
    assert "placeholder-key" not in repr(provider)


def test_keyless_requests_send_no_key_header() -> None:
    transport = FakeTransport([ok({"data": []})])

    fetch(FxMacroDataProvider(transport=transport))

    assert "X-API-Key" not in transport.calls[0][2]


def test_keyless_history_window_warns() -> None:
    page = {
        "freemium_window": {"applied": True, "max_days": 90, "cutoff_date": "2026-07-03"},
        "data": [],
    }
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    with pytest.warns(FxMacroDataAccessWarning, match="only from 2026-07-03"):
        fetch(provider)


def test_retries_rate_limits_then_raises_http_errors() -> None:
    transport = FakeTransport(
        [
            FxMacroDataResponse(429, {"detail": "slow down"}, retry_after_seconds=0.0),
            ok({"data": []}),
        ]
    )
    assert fetch(FxMacroDataProvider(transport=transport)) == []
    assert len(transport.calls) == 2

    denied = FakeTransport([FxMacroDataResponse(403, {"detail": "subscription required"})])
    with pytest.raises(FxMacroDataHTTPError, match="HTTP 403: subscription required") as exc:
        fetch(FxMacroDataProvider(api_key="placeholder-key", transport=denied))
    assert exc.value.status == 403
    assert "placeholder-key" not in str(exc.value)

    exhausted = FakeTransport(
        [FxMacroDataResponse(503, None, retry_after_seconds=0.0) for _ in range(2)]
    )
    with pytest.raises(FxMacroDataHTTPError, match="HTTP 503"):
        fetch(FxMacroDataProvider(max_retries=1, transport=exhausted))


def test_pagination_must_advance() -> None:
    page = {
        "pagination": {"has_more": True, "next_offset": 0},
        "data": [{"date": "2026-07-31", "val": 1.0, "announcement_datetime": 1_786_105_800}],
    }
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    with pytest.raises(FxMacroDataDataError, match="advance"):
        fetch(provider)


def test_malformed_records_raise() -> None:
    page = {"data": [{"date": "July 2026", "val": 1.0, "announcement_datetime": 1_786_105_800}]}
    provider = FxMacroDataProvider(transport=FakeTransport([ok(page)]))

    with pytest.raises(FxMacroDataDataError, match=r"record\.date"):
        fetch(provider)


def test_constructor_validation() -> None:
    with pytest.raises(ValueError, match="api_key"):
        FxMacroDataProvider(api_key=" ")
    with pytest.raises(ValueError, match="timeout_seconds"):
        FxMacroDataProvider(timeout_seconds=0)
    with pytest.raises(ValueError, match="max_retries"):
        FxMacroDataProvider(max_retries=-1)
