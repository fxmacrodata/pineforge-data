# Backtesting

## Runtime options and reports

::: pineforge_data.backtest.BacktestOptions

::: pineforge_data.backtest.MagnifierDistribution

::: pineforge_data.backtest.BacktestReport

`PineForgeBacktestRunner` accepts only strategy libraries that report PineForge
C ABI 2, which engine releases v0.10.2 through v0.12.3 build. It refuses
libraries built with engine v0.13.x (ABI 3) or v1.0.0 (ABI 4) with an
`EngineBacktestError` such as "PineForge ABI mismatch: strategy reports 4,
expected 2". The release container and the FastAPI server do not use this
class.

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
