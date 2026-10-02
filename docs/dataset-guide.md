# Dataset Source and Assumption Guide

## Data Use Summary

RiskSignal Engine uses public interfaces for optional live retrieval and committed,
project-authored synthetic data for its reproducible demonstration. The repository
contains no proprietary data, private social content, real client records, confidential
S&P Global or Crisil material, scraped article bodies, or live API dumps.

Every committed runnable artifact is declared in `data/sources.yaml` with a
classification, redistribution statement, SHA-256 checksum, and material assumptions.
The `python -m risk_engine validate` command recalculates those checksums and fails when
an artifact no longer matches its manifest entry.

## Source Inventory

| Source or artifact | Nature | Used for | Committed | Important constraint |
|---|---|---|---|---|
| GDELT DOC API | Public news-search API | Optional live headline metadata | No | Headline and public metadata only; no article-body scraping |
| Bluesky Public AppView | Public social-search interface | Optional live public posts | No | Search or authentication availability can change |
| `data/sample/gdelt_articles.json` | Synthetic, GDELT-shaped | Offline news ingestion | Yes | Three fictional records; not captured from GDELT |
| `data/sample/bluesky_posts.json` | Synthetic, Bluesky-shaped | Offline social ingestion | Yes | Three fictional records; not captured from Bluesky |
| `data/evaluation/nlp_golden.json` | Synthetic regression set | Deterministic NLP behavior | Yes | Eight authored cases; not a real-world accuracy sample |
| `data/nlp/issuer_watchlist.json` | Synthetic configuration | Entity resolution | Yes | All issuers, aliases, sectors, and tickers are fictional |
| `data/nlp/event_taxonomy.json` | Project-authored configuration | Event labels and severity priors | Yes | Priors are prototype assumptions, not calibrated risk estimates |
| `data/portfolio/portfolio.json` | Synthetic portfolio | Stress valuation | Yes | Eight fictional USD positions across four asset classes |
| `data/portfolio/scenarios.json` | Synthetic scenario matrix | Event-to-shock mapping | Yes | Shocks are illustrative, not forecasts or regulatory scenarios |

The manifest groups seven checksummed artifacts because the two public interfaces are
described as live sources rather than committed datasets.

## Public Live Interfaces

### GDELT DOC API

- Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`.
- Access method: unauthenticated HTTPS GET using Article List JSON output.
- Fields retained: title, public URL, publication timestamp, language, domain, source
  country, and an optional public social-image URL.
- Transformation: only the headline is analyzed; the project does not fetch or
  redistribute article bodies.
- Known limitations: rate limits, incomplete coverage, upstream duplicates, metadata
  errors, schema changes, and service availability.

### Bluesky Public AppView

- Endpoint: `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`.
- Access method: public GET where supported; a provider may require a bearer token.
- Fields retained: public post text, AT URI, public web URL, creation timestamp,
  declared language, public author identifiers, and public engagement counts.
- Transformation: AT URIs are mapped to public `bsky.app` links.
- Known limitations: provider-specific access, changing ranking, moderation and
  deletion, rate limits, and incomplete search coverage.

Live responses are runtime data and are not committed automatically. The adapters use
bounded retries and record source failures separately. A failed live request never
causes synthetic fixture data to appear in the same run.

## Synthetic Fixtures

The six fixture records are hand-authored examples using fictional companies, domains,
accounts, events, and statements. Reserved `.example` domains make their status
visible. They preserve the source-specific shapes needed to test validation,
normalization, timestamps, URLs, language, authorship, deduplication, and provenance.

Their purpose is repeatability, not representativeness. They do not support claims
about current events, source coverage, production data quality, or financial-market
behavior.

## NLP Evaluation and Models

The eight-case golden set covers all supported event categories and specifies expected
deterministic event, sentiment, and entity outputs. Exact agreement on this set is a
regression result for authored examples, not an estimate of precision, recall, F1,
calibration, bias, robustness, or performance on unseen public text.

Optional model mode references immutable revisions of `ProsusAI/finbert` and
`sentence-transformers/all-MiniLM-L6-v2`. Their weights are downloaded by the user and
remain outside the repository. `data/models.yaml` records source links, revisions,
license information available from the publishers, and language or length limitations.

## Portfolio and Scenario Assumptions

The USD 55.50 million baseline portfolio contains eight fictional positions: loans,
bonds, equities, and derivatives for four fictional issuers. Values, durations, credit
parameters, delta exposures, and DV01 values are authored solely to exercise the
simplified valuation paths.

Scenario shocks are configuration, not learned predictions. Macroeconomic and
geopolitical events apply portfolio-wide; other event types apply only to resolved
issuers. An entity-scoped scenario with no matching position returns an explicit
zero-position result rather than stressing unrelated holdings.

Outputs are illustrative scenario calculations. They are not forecasts, investment
recommendations, credit opinions, regulatory capital results, or evidence about any
real institution.

## Provenance Retained at Runtime

Each normalized document retains the source name and type, source identifier, original
URL when available, query, publication and retrieval timestamps, language, public
author metadata where applicable, synthetic flag, and normalized-content hash. Each
risk signal adds model or rule revisions, entity evidence, classification confidence,
impact factors, and a stable link to its source document.

Runtime SQLite databases and generated validation reports live under the ignored
`data/runtime/` directory. They can be deleted and recreated from the committed
artifacts.

## Change Procedure

When a committed data or configuration artifact changes:

1. Confirm that its source classification and redistribution statement remain true.
2. Record any new assumption or transformation in this guide and `data/README.md`.
3. Recalculate the SHA-256 value in `data/sources.yaml`.
4. Update the affected golden expectations or tests deliberately.
5. Run `python -m risk_engine validate` and the full test suite.
6. Record the change and evidence in `progress.md`.
