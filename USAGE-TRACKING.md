# Refreshing image usage

`image-inventory.json` distinguishes collection batches from observed WordPress usage. Repository presence, an import record and a current page reference are separate facts. A missing match never means “unused.”

## Current status meanings

| Status | Meaning |
| --- | --- |
| `new_not_deployed` | Added by the new intake without a deployment through that intake. Retained while no positive import/use evidence appears; not a claim about prior use elsewhere. |
| `existing_unverified` | Existing artwork without a verified current reference or known import mapping in this audit. |
| `imported_unconfirmed` | Import evidence exists, but no current published reference was found within the audit scope. Retained attachment IDs are historical evidence, not proof that the attachment still exists. |
| `in_use` | A matching published image, inline background or featured-image reference was observed during the dated audit. |

A later audit replaces the current placement list. If a previously confirmed placement disappears, its evidence is retained in that image's `usage.placement_history`; the current status becomes unconfirmed unless another positive match exists. A prior `in_use` label does not remain current indefinitely.

## Run a read-only audit

Use Python 3.9 or later from a checkout of this repository. The script uses the Python standard library and public WordPress REST requests; it needs no credentials and does not change WordPress.

```sh
python3 scripts/refresh-image-usage.py
```

The default run prints a JSON summary and leaves the inventory untouched. It reads the registry's known attachment IDs, resolves their public media URLs, and scans all published posts and pages. It checks REST pagination totals and unique post IDs, and refuses to write a partial or inconsistent audit. Unreturned public media records are counted explicitly; their existing attachment IDs are retained.

To save a separate audit report:

```sh
python3 scripts/refresh-image-usage.py --report usage-audit-report.json
```

To update the local inventory after a successful audit:

```sh
python3 scripts/refresh-image-usage.py --write
```

`--write` replaces the local JSON atomically. It preserves asset IDs, files, catalog keys, categories, existing attachment IDs and prior placement history. Publishing the changed JSON to the gallery is a separate repository action.

## Optional import mapping refresh

An authorized WPVibe read can provide a sanitized mapping export in this shape:

```json
{
  "rows": [
    {
      "attachment_id": 12345,
      "catalog_key": "the-existing-inventory-key",
      "attached_file": "2026/11/example-image.jpg"
    }
  ]
}
```

Only these mapping fields are consumed. Keep the export local; do not publish raw database output, credentials or internal database identifiers. The script matches `catalog_key` to an existing inventory row, retains prior attachment IDs, and stores sanitized import evidence. Unknown catalog keys are reported rather than creating new assets.

```sh
python3 scripts/refresh-image-usage.py --imports import-mappings.json
python3 scripts/refresh-image-usage.py --imports import-mappings.json --write
```

`--include-source-urls` optionally matches same-site uploads URLs already recorded as source provenance. For older registry rows that omit those URLs, it reads the corresponding local legacy catalog and requires an exact file/key match. This is useful for original Supremacy blog images copied into the repository. Such a match can establish a current page reference but does not establish a new GitHub import or manufacture an attachment mapping. These references are labeled `original_source_url` in the placement evidence; source-only counts and missing local catalogs are reported separately. External source-site URLs are excluded from this option.

```sh
python3 scripts/refresh-image-usage.py --include-source-urls
python3 scripts/refresh-image-usage.py --include-source-urls --write
```

Use that option when reproducing the initial audit, which included same-site original blog-image references. Without it, the helper reports the narrower known-import reference set.

## Scope and interpretation

Every run records a UTC timestamp, the site, counts and explicit scope. Counts of references represent distinct asset/post associations; several occurrences of the same asset in one post are combined. Featured images, rendered `<img>`/`<picture>` sources and inline background URLs are inspected. Drafts, private content, templates, external Elementor CSS and unrecognized CDN transformations remain outside the audit.

The initial 25 November 2026 audit covered 301 published posts and 212 published pages, with 262 mapped imports, 244 confirmed assets and 1,279 asset/post references. Those are a dated snapshot, not permanent totals.

## Pool collection and the Swapper

The installed Swapper v1.5.4 reads the eight legacy catalogs: plumbing, electrical, HVAC, pest, air conditioning, garage doors, holiday lighting and heating. The new `pool-leak-detection.json` collection prepares reviewed imagery and metadata; it is not yet connected to that automatic import list. Adding an image or refreshing its usage record does not import or replace a WordPress image. Pool import support and selected page replacements require the separate Swapper/deployment workflow.
