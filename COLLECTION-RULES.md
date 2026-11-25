# Artwork collection and usage rules

These rules govern the pool intake begun on 2026-11-25 and later batches that use the same workflow. They document the user's collection requirements and the repository's existing metadata and import conventions. A later explicit user instruction can change the scope; record that change in the relevant batch.

## 1. Keep each intake identifiable

- Assign every intake a stable batch ID and collection date. For this intake, use `pool-leak-detection-intake-2026-11-25`.
- Give every accepted asset an immutable ID, its first-added batch/date, source record and repository path. A readable title may change; the asset ID must not.
- Add pool images to their own collection and batch. Preserve all existing file paths, catalog keys, asset IDs and WordPress mappings. Do not reorganize prior assets to accommodate a new category.
- Classify by visible subject and intended topic, independently of batch membership and WordPress usage. A new batch means newly collected in this workflow; it does not prove that an image has never appeared elsewhere.
- Keep unavailable, excluded and held candidates in the source/intake record. Only accepted, present files belong in downloadable gallery results and active import catalogs.
- Record broad communities and reference articles separately from individual image candidates. A resolved resource URL does not count as accepted artwork. A community reference does not authorize collecting unrelated feed imagery to fill the gallery.

## 2. Collect and inspect the actual image

- Use the requested source pages and record the exact page and original image URL. Use the best available source file, not duplicate responsive sizes or a screenshot of the webpage.
- Visually inspect each candidate, including its edges, at a useful/native size. Reject visible people or body parts, including hands, arms, feet and cropped technicians. Reject visible watermarks, prominent external source logos, promotional graphics, and unrelated imagery.
- Do not crop out, erase or replace a watermark or source logo to make an otherwise rejected asset acceptable.
- Exclude GIFs, Lottie animations, videos and video posters from this photo intake. Existing animations are outside the image replacement scope.
- Hold uncertain, conspicuously rendered, text-heavy or unsuitable imagery for a separate decision. Do not describe an uncertain image as a verified photograph or a real Supremacy project.
- Record native/display dimensions and placement limits. Small images may be accepted for supporting use when useful; do not enlarge them and present them as high-resolution hero images.
- Record the review result, date, reason and reviewed file hash. A change to the image bytes invalidates an earlier byte-specific review and requires rechecking.

## 3. Separate provenance from public descriptions

Preserve source names, source page URLs, original image URLs, original source labels, retrieval dates, source hashes and any permission evidence in provenance records. Record the authorization actually supplied; do not invent a source license or make a blanket licensing claim. Public availability alone is not a rights record.

For each accepted image, provide four nonempty, plain-text `public_metadata` fields: `title`, `alt`, `caption` and `description`. Describe what the image visibly shows. Keep supplier boilerplate, asset reference numbers, filename hashes, internal IDs and download labels out of these fields. Retain meaningful equipment models, ratings, measurements and other useful subject details when supported.

Do not invent a city, customer, Supremacy technician, completed job, leak diagnosis or repair result from an image or its source title. Source labels may remain in provenance even when they overstate what is visible.

For newly collected external assets, remove embedded source EXIF/IPTC/XMP and other unnecessary metadata after preserving the provenance record. Apply orientation before removing its metadata so the displayed image stays correct. Record both original and final hashes. Metadata cleanup must not erase the separate provenance record or alter visible pixels to disguise ownership.

## 4. Deduplicate without breaking old references

- Compare source URLs, exact byte hashes and decoded image content across the new batch and all existing active catalogs; account for re-encoding and size variants. Use perceptual matching to identify near-duplicate candidates, then visually confirm them.
- A duplicate should refer to the existing canonical asset instead of becoming a second downloadable copy. Record the duplicate relationship and additional source evidence.
- Preserve an existing canonical file, ID and path when it already has catalog or usage references. Never silently replace its bytes with a different source image.
- Keep original WordPress media archives separate from active reusable artwork. An archive entry is not automatically a replacement candidate.

## 5. Track collection, import and actual use separately

| Fact or status | Required evidence | What it does not establish |
| --- | --- | --- |
| Collected / in repository | Accepted file exists at the recorded repository path, with a verified hash | A WordPress import or page placement |
| Imported into WordPress | Verified site, attachment ID and import record mapped to the asset | That any page currently displays it |
| Confirmed in use | Verified page/post URL and ID, exact image placement, matching asset/attachment evidence and check time | That other unmapped copies do not exist |
| Usage unverified | Mapping absent, incomplete or stale; no complete placement check | That the image is unused |
| No use found in a defined audit | A dated audit with explicit sites, post types and placement coverage | A universal or permanent “never used” claim |

Store multiple placements when an asset appears more than once. Preserve historical usage evidence when a placement is replaced, and distinguish historical use from currently verified use. An original WordPress attachment ID in a provenance file is not a newly verified import of the repository asset.

Do not label all legacy images “used,” or all new images “unused.” Never infer unused status solely from an empty attachment mapping. Display the batch and verification state plainly so users can distinguish new intake from older inventory without losing the evidence.

## 6. Pool subject taxonomy

Use these categories when a finally accepted image actually supports them. Keep secondary tags for a finer match; do not duplicate the underlying file to place it in several categories.

| Category | Suitable visible subjects from this intake |
| --- | --- |
| Diagnostic equipment | Inspection tool cases, hoses and leak-detection equipment |
| Water loss and evaporation | Waterline observations, a bucket test, mist over the pool surface |
| Underground plumbing | Exposed pipes, return connections, excavation and under-deck access |
| Structural and fitting inspection | Pool finish, coping, tile waterlines and fittings being inspected |
| Skimmer inspection | Skimmer lids, openings and surrounding inspection markers |
| Pump and equipment leaks | Pump connections, visible drips, equipment and repair tools |
| General pool context | Pool shapes, vinyl liners, entry steps and wider pool views |
| Autofill and water-level control | Float valves, autofill chambers, supply shutoffs and water-level controls |
| Pool heater equipment | Heater cabinets, controls, plumbing connections and identifiable heater components |
| Freeze protection | Freeze-protection controls, temperature sensors and identifiable protection components |
| Winter pool care | Pool covers, winterizing plugs, drained fittings and clearly shown seasonal preparations |
| Cold-weather pool conditions | Visible snow or ice around a pool, ladder or equipment, without inferring the cause or a damage diagnosis |
| Pool efficiency | Variable-speed pump controls, pool covers and identifiable water- or energy-management equipment |
| Pool maintenance | Filters, baskets, gauges, cleaning equipment and maintenance components without people or body parts |

Use general pool views as contextual imagery, not evidence of a leak. Do not claim coverage of specialist topics such as main-drain testing, pressure testing or spa diagnostics unless a reviewed asset actually shows the relevant subject.

The related pool care intake uses its own `pool-care-intake-2026-11-25` batch and `pool-care` collection. Keep its images separate from the first leak-detection batch while allowing references to canonical files from either collection. Classify the visible equipment or preparation without inferring its operating condition, successful freeze protection, a completed maintenance procedure or measured efficiency savings. Seasonal scenery alone does not verify a protective function.

## 7. Gallery collection is separate from WordPress deployment

Adding an accepted image to the repository or gallery does not select a WordPress page, import media, replace an image or publish a page. The later replacement workflow must select the specific repository asset and placement, verify file availability, apply its clean public metadata, preserve a replacement manifest and record the resulting import/use evidence. A source-site URL must never substitute for a missing GitHub asset during import.

For blog replacements, preserve suitable existing images without people and replace only the approved targets. Follow the user's applicable Elementor presentation instructions and archive/reference checks in that separate replacement task. Never delete WordPress media merely because a new gallery file exists.
