# Server components

Most users run the server image built from `docker/server.Dockerfile` or submit
work through `FastApiBacktestClient`. The packaged `pineforge-backtest-server`
command reports ready only where the `pineforge-release` toolchain is
installed, as in that image. These objects support applications that embed the
service or manage its compiled-strategy cache directly.

::: pineforge_data.server.create_app

::: pineforge_data.server.BacktestService

::: pineforge_data.server.BacktestServiceError

::: pineforge_data.compile_cache.CompileCache

The running service also publishes an interactive OpenAPI schema at `/docs`.
See the [server guide](../server.md) for HTTP behavior, concurrency, security,
and deployment configuration.
