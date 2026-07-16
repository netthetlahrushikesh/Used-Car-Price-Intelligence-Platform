# Source Evaluation Template

Use this before writing a scraper or connector.

## Source

```text
source_name:
source_url:
market:
source_type: partner_feed | public_page | open_dataset | manual_seed | user_submitted
evaluation_date:
owner:
```

## Intended Use

```text
purpose:
commercial_use: yes | no | unknown
frequency:
expected_records_per_run:
expected_fields:
```

## Policy Review

```text
terms_url:
robots_url:
automated_access_allowed: yes | no | unknown
commercial_extraction_allowed: yes | no | unknown
permission_required: yes | no | unknown
permission_status: not_requested | requested | granted | denied
```

Notes:

- Quote or summarize only the specific policy clauses that matter.
- Store links and review date.
- If permission is required, do not build a production scraper until permission is granted.

## Data Risk

```text
contains_personal_data: yes | no | unknown
contains_seller_contact_data: yes | no | unknown
contains_private_account_data: yes | no | unknown
```

Allowed fields:

```text

```

Disallowed fields:

```text

```

## Technical Feasibility

```text
static_html: yes | no | unknown
javascript_required: yes | no | unknown
stable_listing_id: yes | no | unknown
pagination_or_scroll:
rate_limit_expectation:
expected_breakage_risk: low | medium | high
```

## Data Quality Expectations

```text
coverage:
freshness:
duplicate_risk:
missing_field_risk:
field_normalization_risk:
```

## Decision

```text
status: approved | blocked | needs_permission | research_only
reason:
next_action:
```
