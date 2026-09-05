# `build_web/`

Stage 2 of the build: the prepared CSVs become the denormalised JSON the
static site fetches.

`build_web_data.py` reads `data/normalized/{entities,diary,references}.csv`
plus the optional `rejser` add-on, and writes `web/data/*.json` — the
Places demo shapes and `manifest.json`, which carries the build's
provenance (each raw source's filename and SHA-256, read from
`data/normalized/_source.json` when this checkout does not hold the
sources itself).

`parse_rejser_htm.py` used to sit here. It parses a raw HTM table into a
TSV — ingest, not build — and moved to
[HCA-Diary-data-cleaning](https://github.com/ogierMontanus/HCA-Diary-data-cleaning)
as `scripts/enrichment/parse_rejser_htm.py`. See
[`docs/pipeline/README.md`](../../docs/pipeline/README.md).
