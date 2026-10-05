# Data Sources and Provenance

## Data Policy

This project uses only public source interfaces and clearly identified synthetic data.
It does not contain confidential client data, real S&P Global or Crisil engagement
data, private social-media content, scraped article bodies, or proprietary datasets.

Runtime API responses are written only to the ignored `data/runtime/` directory. A
runtime record retains its source identifier, original URL, query, publication time,
retrieval time, language, author when public, synthetic flag, and content hash.

## Live Sources

### GDELT DOC API

- Nature: public global news search API.
- Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`.
- Access: unauthenticated HTTPS GET request using Article List JSON output.
- Retained fields: headline, article URL, publication time, language, domain, source
  country, and optional social-image URL.
- Transformation: the headline is the analyzed text; full article bodies are not
  scraped or redistributed.
- Assumption: GDELT coverage is broad but not exhaustive and metadata may contain
  upstream errors or duplicates.
- Documentation: <https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/>.

### Bluesky Public AppView

- Nature: public social-media search interface.
- Endpoint: `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`.
- Access: public GET where supported by the AppView provider; some deployments require
  a bearer token supplied through the local `RISK_ENGINE_BLUESKY_BEARER_TOKEN`
  environment variable.
- Retained fields: public post text, AT URI, public web URL, creation time, declared
  language, public handle, DID, CID, and public engagement counts.
- Transformation: AT URIs are converted to public `bsky.app` post URLs.
- Assumption: search availability and ranking can change, and deleted or moderated
  posts may no longer be returned.
- Lexicon: <https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/searchPosts.json>.

Before using live retrieval or making a final submission, review current source terms
and retention restrictions. Live responses are not committed automatically.

Live adapters apply bounded retries to transport failures, rate limits, and transient
server errors. Terminal errors contain only the source and exception class rather than
response bodies that could expose upstream details.

The committed `data/live-snapshots/2026-10-05-public-metadata.json` is a metadata-only
connectivity record. It retains endpoint, query, status, count, authentication, and
terms notes, but no article or post body. The Bluesky entry records a 403 without a
bearer token; this is an explicit authentication outcome, not a fixture fallback.

## Committed Fixtures

The two files under `data/sample/` are hand-authored synthetic examples. Names,
domains, handles, DIDs, events, and statements are fictional. Reserved `.example`
domains prevent the fixtures from being mistaken for real publications or accounts.

The fixtures exist to make tests and the offline demonstration deterministic. They
follow the normalized fields exposed by their corresponding live adapter but are not
claimed to be API captures or evidence about real organizations.

Checksums are recorded in `data/sources.yaml`. Any fixture edit requires updating its
checksum and noting the change in `progress.md`.

## Synthetic Replay Bundle

The two files under `data/replay/` form a separate four-record, offline-only scenario.
They are hand-authored news- and social-shaped statements about fictional Aurora Bank,
use reserved `.example` domains, and are inspired only by the general pattern of the
public March 2023 banking-sector stress episode. They contain no copied article or post
text and make no claim about a real issuer.

Replay mode is distinct from both fixtures and live retrieval. It exists to demonstrate
that the unchanged deterministic NLP pipeline can organically cross the impact trigger
and run the configured synthetic stress scenario. Each replay file is checksummed in
`data/sources.yaml`; replay records never replace a failed live source.

## NLP Evaluation and Configuration

`data/evaluation/nlp_golden.json` is a project-authored synthetic regression set. Its
eight cases cover every event-taxonomy category and expected deterministic sentiment
and issuer matches. It protects implementation behavior but is deliberately not
presented as evidence of real-world model accuracy.

`data/nlp/issuer_watchlist.json` contains only fictional companies and aliases.
`data/nlp/event_taxonomy.json` contains the project-authored category descriptions,
keywords, and prototype severity priors. These configuration artifacts and the golden
set are checksummed in `data/sources.yaml`.

Model identifiers, immutable revisions, published licensing information, and known
limitations are recorded in `data/models.yaml`. Model weights are downloaded into the
ignored cache directory only when `model` mode is selected; no weights are committed.
The default `deterministic` mode uses transparent project-authored rules so tests and
offline demonstrations remain reproducible. Mode selection is explicit and a failed
model load is never silently replaced with deterministic output.

## Synthetic Portfolio and Scenarios

`data/portfolio/portfolio.json` is a fictional USD portfolio with eight positions
covering loans, bonds, equities, and derivatives. Its companies align with the
fictional issuer watchlist. Values, credit parameters, durations, delta exposures,
and DV01 measures are project-authored solely to exercise the prototype calculations.

For derivative positions, `delta_exposure` is a signed USD exposure and the configured
underlying shock is a decimal return. DV01 uses USD per basis point and is entered as a
positive loss for a +1 bp interest-rate move; positive `rate_shock_bps` means rates
rise. The exact linear calculation is `P&L (USD) = delta_exposure (USD) x
underlying_shock (decimal) - DV01 (USD/bp) x rate_shock_bps (bp)`, followed by `value
after = value before + P&L`. It is an illustrative approximation, not a full derivative
pricing model.

`data/portfolio/scenarios.json` maps each event category to one explicit set of shocks.
Macroeconomic and geopolitical scenarios apply portfolio-wide; issuer-specific events
apply only to resolved entities. These shocks are illustrative assumptions rather
than forecasts, calibrated regulatory stress tests, investment advice, or evidence
about real institutions. Both files are versioned and checksummed in
`data/sources.yaml`.

`data/portfolio/sector_proxy.json` maps broad real-world sector labels to matching
synthetic sectors. Any stress result based on a non-synthetic live signal is labelled
`illustrative sector proxy`; it must never be read as issuer exposure.
