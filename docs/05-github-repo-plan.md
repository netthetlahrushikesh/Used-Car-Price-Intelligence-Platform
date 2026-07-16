# GitHub Repository Plan

## Current Local State

This project folder is initialized as its own local Git repository:

```text
<local workspace>/Used Car Price Intelligence Platform
```

This prevents the project from accidentally using a parent user-level Git repository.

## Recommended GitHub Repository

Recommended name:

```text
used-car-price-intelligence
```

Recommended visibility while building:

```text
private
```

Reason:

- Early scraping and data design work can expose source assumptions.
- We may create experimental data contracts and source notes.
- Public release should happen after the data policy, README, and first clean demo are ready.

## Repository Rules

- Do not commit raw data.
- Do not commit secrets.
- Do not commit browser traces that contain sensitive tokens.
- Do not commit `.env` files.
- Keep old notebook repository separate.
- Reference the old repository only as historical inspiration.

## Initial Branch Strategy

```text
main       stable project foundation
develop    optional integration branch later
feature/*  implementation work
```

For now, `main` is enough.

## Initial GitHub Setup Checklist

When creating the GitHub repo:

- Add description: `Data-first used-car market intelligence platform for fair price estimation and listing analytics.`
- Keep it private initially.
- Add no template files from GitHub UI; this local repo already owns the foundation.
- Add branch protection after the first push.
- Add issues/projects after the first implementation milestone is clear.

## Remote Creation Options

Using GitHub CLI:

```powershell
gh repo create netthetlahrushikesh/used-car-price-intelligence --private --source . --remote origin --push
```

Manual GitHub UI:

1. Create an empty private repository named `used-car-price-intelligence`.
2. Do not initialize it with README or `.gitignore`.
3. Add the remote locally.
4. Push `main`.

## Decision Needed

Before pushing to GitHub, confirm:

- Repository name.
- Public or private.
- Whether to include an MIT license, Apache-2.0 license, or no license yet.
