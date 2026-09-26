# Controlled experiment report

Model: `codex/gpt-6-luna`  
Phase: `raw_generation`  
Dispatch timestamp: `2026-09-25T22:20:49.811Z`  
Observed completion UTC: `2026-09-25T22:21:50Z`

Implemented a standalone Python application using only the standard library. It reads newline-delimited JSON requests, keeps balances for the lifetime of the process, validates request shape and types before checking funds, and writes one compact JSON response per input line. Invalid JSON lines are reported as `invalid_input` without terminating the stream.

Tests cover initial balances, transfers in both directions, conservation, purchase behavior, invalid inputs, validation precedence, insufficient-funds nonmutation, and process-level JSON-lines behavior.

Uncertainty: provisioning/queue split and usage are unavailable. No exact active-agent time or cost is claimed. This is a live generator sample, not a scored speed win. No external reference implementation or scenario files were inspected.
