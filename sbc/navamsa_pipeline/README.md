# Navamsa D-9 Forward Time-Series and Intraday Trigger Pipeline

Production-grade Python pipeline for forward Navamsa D-9 mapping, KP/SBC rule-based intraday triggers, CSV/XLSX export, and validation/backtest.

## Run
poetry run python cli.py --start 2026-09-01 --end 2026-09-30 --granularity 1m --ayanamsha KP --ephemeris de440 --outdir ./outputs

## Outputs
- navamsa_monthly.csv
- intraday_triggers.csv
- validation report

## Config
rules/rules_spec.yaml controls ayanamsha, ephemeris, weights, thresholds.

## Acceptance
- Navamsa mapping matches reference examples
- Exports with metadata
- Validation harness produces precision/recall/avg move
