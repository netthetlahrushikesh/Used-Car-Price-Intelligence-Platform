# Cars24 Hyderabad Initial Source Evaluation

## Source

```text
source_name: Cars24
source_url: https://www.cars24.com/
market: Hyderabad
source_type: public_page
evaluation_date: 2026-06-24
owner: project
```

## Context

The old notebook scraped a Cars24 Hyderabad listing URL. That makes Cars24 useful as historical context, but this new project is being built to a startup-grade standard. The standard is higher than "can a script collect rows?"

## Policy Review

References checked on 2026-06-24:

- Terms and Conditions: https://www.cars24.com/terms-and-conditions/
- Robots file: https://www.cars24.com/robots.txt

Relevant findings:

- The Cars24 terms say users must not access or attempt to access the website or services through automated means, including bots, scrapers, crawlers, spiders, or scripts, without prior written permission.
- The terms also restrict scraping, data mining, indexing, or extracting website content or information for commercial purposes.
- The robots file exists and includes multiple disallowed paths. The original notebook URL path was not enough by itself to approve scraping because terms still control allowed behavior.

## Decision

```text
status: needs_permission
reason: current terms block automated access without prior written permission and restrict commercial scraping/data extraction
next_action: do not build a production Cars24 scraper unless permission is obtained; use a manual seed dataset or permissioned feed for the first pipeline
```

## Safe Use In This Project

Allowed:

- Use the old notebook as historical reference.
- Use manually typed sample records for parser tests.
- Use Cars24 as a potential partnership target.
- Use public pages manually for small qualitative research if consistent with terms.

Not allowed for this production project without written permission:

- Automated scraping.
- Commercial data extraction.
- Bulk collection.
- Circumventing access controls or anti-bot systems.
