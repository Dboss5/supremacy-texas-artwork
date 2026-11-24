# Supremacy image libraries

The active artwork library contains **1,277 repository images across eight service galleries**. Open the [live dashboard](https://supremacy-texas-artwork.vercel.app/) or [index.html](index.html), then search or filter a gallery. Every gallery uses committed repository files for previews and downloads and retains links to the original sources.

## Collections

| Gallery | Images | Sources | Catalog | Source inventory |
| --- | ---: | ---: | --- | --- |
| [HVAC](hvac.html) | 226 | 8 | [hvac.json](hvac.json) | [HVAC-SOURCES.md](HVAC-SOURCES.md) |
| [Air Conditioning](air-conditioning.html) | 188 | 8 | [air-conditioning.json](air-conditioning.json) | [AIR-CONDITIONING-SOURCES.md](AIR-CONDITIONING-SOURCES.md) |
| [Plumbing](plumbing.html) | 157 | 7 | [plumbing.json](plumbing.json) | [PLUMBING-SOURCES.md](PLUMBING-SOURCES.md) |
| [Electrical](electrical.html) | 100 | 7 | [electrical.json](electrical.json) | [ELECTRICAL-SOURCES.md](ELECTRICAL-SOURCES.md) |
| [Pest Control](pest.html) | 343 | 6 | [pest.json](pest.json) | [PEST-SOURCES.md](PEST-SOURCES.md) |
| [Garage Doors](garage-doors.html) | 112 | 3 | [garage-doors.json](garage-doors.json) | [GARAGE-DOOR-SOURCES.md](GARAGE-DOOR-SOURCES.md) |
| [Holiday Lighting](holiday-lighting.html) | 134 | 5 | [holiday-lighting.json](holiday-lighting.json) | [HOLIDAY-LIGHTING-SOURCES.md](HOLIDAY-LIGHTING-SOURCES.md) |
| [Heating](heating.html) | 17 | 4 | [heating.json](heating.json) | [HEATING-SOURCES.md](HEATING-SOURCES.md) |
| **Total** | **1,277** | | | |

Source counts are per gallery; a company may contribute to more than one collection. The 14 heating additions are already included in the 226-image HVAC total.

## Downloads and repository availability

All **1,277 catalog file paths are present**, with **zero pending files**. Gallery cards support individual downloads, selection of visible images, and downloads of a selected group. The download controls use each entry's committed `file` path.

The following ZIPs contain the corresponding repository images:

| Download | Images |
| --- | ---: |
| [Garage door images](garage-door-images.zip) | 112 |
| [Holiday lighting images](holiday-lighting-images.zip) | 134 |
| [Heating images](heating-images.zip) | 17 |
| [HVAC heating additions](hvac-heating-additions.zip) | 14 |

The Holiday Lighting page and dashboard link to the complete rebuilt 134-image archive. The initial asset recovery is recorded in [asset-repair-report.json](asset-repair-report.json) and [asset-recovery-provenance.json](asset-recovery-provenance.json). The 75 selected blog-original additions, current catalog totals and updated Garage Door and Heating ZIP checks are recorded in [blog-reuse-integration-report.json](blog-reuse-integration-report.json).

The owner approved public recovery of the remaining 172 catalog images and reconstruction of the Holiday Lighting ZIP. Original source names, URLs, and existing product marks remain recorded for attribution. A gallery entry does not establish that an image depicts a Supremacy project or a verified Texas location.

## Reviewed subset for blog selection

[blog-approved-artwork.json](blog-approved-artwork.json) lists **182 reviewed images for blog selection**: 107 existing catalog images and the 75 reused Supremacy originals. Each entry includes clean public metadata, its exact Git image-blob hash, and actual source dimensions. The review covers visible people and body parts; generic icons and logos are allowed. All other catalog images require visual review before blog selection. Recheck a listed image if its file bytes change from the recorded hash.

## Reused Supremacy blog artwork

The active catalogs include **75 selected images from existing published Supremacy Services blog posts**: 31 garage-door images, 25 plumbing images, 17 pest images, one electrical image and one heating image. Each selected image was visually reviewed and contains no realistic person or body part. Generic icons and existing Supremacy logos are preserved. The original image bytes are copied into the repository, and clean titles, descriptions, captions and alt text describe the artwork itself.

[blog-reuse-provenance.json](blog-reuse-provenance.json) records original article and image URLs, source media references, dimensions and byte checksums. These source media references identify provenance; they are not newly verified GitHub imports in WordPress. New imports receive their own media records through the Swapper.

## Public image metadata

Every active catalog entry contains a `public_metadata` object with four nonempty plain-text fields:

```json
{
  "public_metadata": {
    "title": "Outdoor air conditioning condenser",
    "alt": "Outdoor air conditioning condenser beside a house",
    "caption": "Outdoor air conditioning condenser.",
    "description": "Outdoor air conditioning condenser beside a house."
  }
}
```

Gallery titles, image alt text, search labels, and previews use these fields. Supremacy Before/After Swapper uses reviewed embedded overrides first, validated `public_metadata` second, and its metadata cleanup fallback when neither is available. This keeps catalog numbers, filename hashes, supplier boilerplate, and reference labels out of public WordPress image metadata.

The initial 1,202-image metadata review included **592 visually checked images** and **610 cleaned source labels**. The 75 blog-original additions were separately visually reviewed and given clean public descriptions. Meaningful equipment models, ratings, bulb types, and measurements remain intact. Original `title`, `source`, `source_page`, and original asset URL fields retain their provenance values and are separate from the public descriptions.

The Swapper imports only repository files that pass its availability checks. A source URL remains an attribution record and does not replace a missing repository asset during import.

## Original WordPress media archive

The [Original Image Archive](original-media-archive.html) lists **26 preserved original media records** with download links, source records, byte sizes, and checksums. Its files remain on the [archive-snapshot-before-artwork-recovery branch](https://github.com/Dboss5/supremacy-texas-artwork/tree/archive-snapshot-before-artwork-recovery).

The archive is separate from the 1,277 active gallery images. Its [status record](https://github.com/Dboss5/supremacy-texas-artwork/blob/archive-snapshot-before-artwork-recovery/ARCHIVE-STATUS.md) preserves the original retrieval history, including any historical failures.

## Earlier collection records

[COMPANY-SITE-REVIEW.md](COMPANY-SITE-REVIEW.md), [SOURCES.md](SOURCES.md), and [collection.json](collection.json) describe the earlier 102-image company-site collection. They remain as historical provenance. The eight catalogs listed above define the current active galleries and import inventory.
