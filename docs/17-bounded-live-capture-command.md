# Bounded Live Capture Command

Date: 2026-06-24

Purpose: add the first local command that can capture one public Spinny listing page into the extracted payload
contract.

## Scope

Implemented:

- one source: Spinny,
- one page URL at a time,
- listing-card DOM text extraction,
- extracted payload JSON output,
- immediate payload contract validation,
- offline tests for card-text parsing and payload validation.

Not implemented:

- pagination,
- scheduling,
- retries beyond browser timeout,
- canonical data writes from live capture,
- detail-page enrichment,
- proxying,
- login/CAPTCHA/anti-bot bypass.

## Optional Dependency

Base parser and quality tests do not require browser automation. Live capture requires the optional acquisition
dependency:

```powershell
python -m pip install -e .[acquisition]
python -m playwright install chromium
```

If the dependency is missing, `capture-spinny-live` exits nonzero with setup guidance and does not write a payload.

## Command

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli capture-spinny-live --output data/tmp/spinny_live_payload.json --json
```

Equivalent explicit form:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli capture-spinny-live --url https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/ --output data/tmp/spinny_live_payload.json --max-records 20 --locality "Nexus Sujana Mall, Kukatpally" --json
```

## Extraction Strategy

The command targets Spinny listing-card containers matching:

```text
[class*='CarListingCardV2__carListingCardV2Root']
```

For each card, it extracts text lines in this expected order:

```text
2025 Mahindra XUV700
20.44 Lakh
AX 7 Luxury Pack Petrol AT 7 STR
EMI Rs 35,385/m*
26.5K km
Petrol
Automatic
TG07
```

The parser converts that text block into raw extracted slots:

- `title`,
- `price`,
- `variant`,
- `emi`,
- `km`,
- `fuel`,
- `transmission`,
- `registration`,
- `locality`.

If locality is not present in a card, the command uses the configured page-level locality fallback.

## Safety Behavior

The command writes only an extracted payload and validates it. It does not yet write canonical silver/gold data.

This keeps the sequence safe:

1. capture page text,
2. write extracted payload,
3. validate extracted payload contract,
4. later run canonical conversion only when validation passes.

## Environment Check

Before installing the optional acquisition dependency, the command returns setup guidance:

```text
Playwright is required for live capture. Install with `python -m pip install -e .[acquisition]` and then `python -m playwright install chromium`.
```

The CLI returns nonzero and no payload file is written.

After installing the dependency in `.venv`, the command successfully captured and validated 20 public Spinny
listing-card records.

First live-capture bug found:

- `Style 1.0L TSI AT` was initially mistaken for a price-like line because of `1.0L`.
- The extractor now treats `Lakh`, `Lac`, `Cr`, and `Crore` as price units for listing-card line detection, but not bare engine-size `L`.

## Next Step

The controlled live smoke command now exists as `spinny-live-smoke`. It now persists a compact Markdown report for
each run so a human can inspect the acquisition result without reading large JSON output.
