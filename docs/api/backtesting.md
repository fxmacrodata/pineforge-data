# Backtesting

## Runtime options and reports

::: pineforge_data.backtest.BacktestOptions

::: pineforge_data.backtest.MagnifierDistribution

::: pineforge_data.backtest.BacktestReport

`PineForgeBacktestRunner` runs a compiled strategy library in-process. It
accepts libraries that report PineForge C ABI 4, which engine 1.x builds. It
refuses older libraries before any strategy call, with an `EngineBacktestError`
that names the engine releases behind their ABI: ABI 2 (engine v0.10.2 through
v0.12.3) and ABI 3 (engine v0.13.x). Rebuild such a library with engine 1.x;
pineforge-data 0.2.0 still reads ABI 2. The release container and the FastAPI
server do not use this class.

A trade's `max_runup` and `max_drawdown` are whole-trade excursions in account
currency, net of entry fees, as engine 1.0's `pineforge.h` documents them.
Headers before 1.0 described them as price travel per unit of quantity, but the
values did not change: on the README quick start, engines 0.11.0 and 1.0.0
report identical excursions for the 88 trades both report. A trade whose
`open_at_end` is true closes a position still open after the final bar, at that
bar's close. Engine 0.11.0 reports no such row, so the README quick start has 88
trades on it and 89 on engine 1.0.0.

::: pineforge_data.backtest.PineForgeBacktestRunner

::: pineforge_data.backtest.EngineBacktestError

## Published release container

::: pineforge_data.docker_runtime.DockerBacktestRuntime

::: pineforge_data.docker_runtime.DockerPrerequisiteError

::: pineforge_data.docker_runtime.DockerExecutionError

::: pineforge_data.release_contract.DEFAULT_RELEASE_IMAGE

::: pineforge_data.release_contract.ReleaseContractError

## Remote FastAPI client

::: pineforge_data.server_client.FastApiBacktestClient

::: pineforge_data.server_client.BacktestServerError
