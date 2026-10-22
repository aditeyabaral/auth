# Alpine vs slim-bookworm vs slim-trixie benchmark

Charts, raw data and scripts behind the pesu-auth pull request that moves the Docker base image to
`python:3.14-slim-trixie`. Not part of the application.

- `data/requests.csv`: one row per request (latency split, container CPU and memory)
- `data/{alpine,slim,trixie}.csv`: the same runs in the `scripts/benchmark/analyze_benchmark.py` format
- `data/meta.json`, `data/cold_start.json`: sizes, final metrics, per-block CPU, cold starts
- `scripts/drive3.py`: the interleaved driver; `analyze3.py`: the statistics; `charts.py`: the charts
- `scripts/Dockerfile.alpine`: the Alpine variant (the Dockerfile with the base image and user commands swapped)
