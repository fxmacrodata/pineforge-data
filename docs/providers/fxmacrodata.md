# FXMacroData macro provider API

`FxMacroDataProvider` implements `MacroDataProvider`. It reads economic
announcements (CPI, policy rates, payrolls, GDP and so on) from the
[FXMacroData API](https://fxmacrodata.com/documentation/reference?utm_source=github&utm_medium=referral&utm_campaign=pineforge-data&utm_content=docs)
and returns `MacroObservation` records with release and vintage timestamps. It
has no market catalog and no bars, so it is not a `MarketDataProvider` and is
not registered for `pineforge-backtest --provider`.

FXMacroData is a commercial API. Without a key only USD is available, limited
to the most recent 90 days and delayed by 15 minutes. Other currencies and full
history need an API key.

## Install

```bash
pip install pineforge-data
```

No extra is needed: the default transport uses the standard library.

## Construct the provider

```python
import os

from pineforge_data import FxMacroDataProvider, MacroRequest


async def us_payrolls():
    async with FxMacroDataProvider(api_key=os.environ.get("FXMACRODATA_API_KEY")) as provider:
        return await provider.fetch_observations(
            MacroRequest(
                key="non_farm_payrolls",
                currency="USD",
                start_ms=1_775_001_600_000,  # 2026-04-01
                end_ms=1_790_812_800_000,  # 2026-10-01
            )
        )
```

`key` is an FXMacroData indicator slug, such as `inflation`, `policy_rate`,
`non_farm_payrolls` or `gdp`. The per-currency list is served by
`GET /v1/data_catalogue/{currency}`. `currency` is a currency code (`USD`,
`EUR`, `JPY` and so on).

The key is sent only in the `X-API-Key` header. It is not placed in URLs,
exception messages or the provider's `repr`.

## Timestamps and vintages

| Field | Taken from |
|---|---|
| `period_end_ms` | UTC midnight of the record's `date` |
| `released_at_ms` | the record's `announcement_datetime` |
| `vintage_at_ms` | when that value became available (below) |

The provider requests `revisions=all` and emits one observation each time a
period's value changed:

- a source vintage (`vintage_status: source_vintage`) is dated by its
  publication time (`publication_at_ns`, else `epoch`);
- a captured snapshot (`vintage_status: captured_snapshot`) is dated by
  `observed_at_ns`, the time FXMacroData read it from the publisher. Its
  `epoch` repeats the original release time, so using it would date a later
  revision back to the first print;
- a vintage is never earlier than `released_at_ms`, and a vintage that repeats
  the previous value is dropped.

Some history was collected after publication and has only a captured snapshot.
Those values are dated by when they were collected, so a backtest set before
that date does not see them. This is deliberate: the alternative is
lookahead.

## Records that are skipped

`MacroObservation` requires a release time, and the provider does not invent
one. These records are left out and counted in `provider.last_skipped` for the
most recent fetch:

| Reason | Meaning |
|---|---|
| `unknown_release_time` | `announcement_datetime` is null (`publication_time_status: unknown`) |
| `assumed_release_time` | the time was derived by FXMacroData from the series' usual publication lag, not captured (`release_time_assumed` or `publication_time_status: assumed_historical`). Pass `include_assumed_release_times=True` to keep them |
| `released_before_period_end` | the release precedes the period date, for example a flash estimate, which `MacroObservation` cannot represent |
| `revision_without_vintage_time` | a revision has no usable availability time |
| `missing_value` | a record or revision has a null value |

## Constructor reference

| Argument | Default | Meaning |
|---|---|---|
| `api_key` | `None` | FXMacroData API key; `None` uses the keyless USD tier |
| `api_url` | `https://api.fxmacrodata.com/v1` | API root |
| `timeout_seconds` | `20.0` | per-request timeout of the default transport |
| `max_retries` | `2` | retries after HTTP 429, 500, 502, 503 or 504 |
| `retry_backoff_seconds` | `1.0` | first retry delay, doubled each attempt; `Retry-After` takes precedence |
| `include_assumed_release_times` | `False` | keep records whose release time was derived rather than captured |
| `transport` | `None` | an `FxMacroDataTransport`; inject one for offline tests or a custom HTTP client |

Pages hold at most 100 records; the provider follows `pagination.has_more` and
`next_offset` until the request is complete.

## Errors and limitations

| Error | Meaning |
|---|---|
| `FxMacroDataHTTPError` | a non-success status after retries; `.status` holds the code (403 for a currency or history the key does not cover) |
| `FxMacroDataDataError` | a response or record cannot be normalized safely |
| `FxMacroDataError` | base class; also raised for network failures |
| `FxMacroDataAccessWarning` | a warning, not an error: the keyless tier cut the requested history short or withheld a release from the last 15 minutes |

- Units come from the response's `value_metadata.source_unit`; `unknown` is
  used when it is absent.
- Responses are not cached. Snapshot them at your job boundary when exact
  replay matters.
- Only the announcements endpoint is used. Release calendars, consensus
  forecasts and FX prices are out of scope for this provider.
