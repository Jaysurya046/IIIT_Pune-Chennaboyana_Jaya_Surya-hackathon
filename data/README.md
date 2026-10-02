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

Before final submission, current source terms and any retention restrictions will be
reviewed again. Live responses will not be committed automatically.

Live adapters apply bounded retries to transport failures, rate limits, and transient
server errors. Terminal errors contain only the source and exception class rather than
response bodies that could expose upstream details.

## Committed Fixtures

The two files under `data/sample/` are hand-authored synthetic examples. Names,
domains, handles, DIDs, events, and statements are fictional. Reserved `.example`
domains prevent the fixtures from being mistaken for real publications or accounts.

The fixtures exist to make tests and the offline demonstration deterministic. They
follow the normalized fields exposed by their corresponding live adapter but are not
claimed to be API captures or evidence about real organizations.

Checksums are recorded in `data/sources.yaml`. Any fixture edit requires updating its
checksum and noting the change in `progress.md`.
