#!/usr/bin/env python3
"""Refresh known artwork usage from public WordPress REST; dry-run by default.

Only standard-library modules are required. Importing this module performs no
network calls and reads no files, environment variables, or credentials.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import datetime as dt
import gzip
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import urllib.parse
import urllib.request

DEFAULT_SITE = "https://supremacyservice.com"
SCOPE = (
    "Published posts and pages: public REST rendered image/picture elements, "
    "inline background URLs and featured image IDs, matched to known attachment "
    "mappings and explicitly enabled source URLs. One placement record means "
    "one asset/post association, not one DOM occurrence. Drafts, private content, "
    "templates and externally generated Elementor CSS are outside this audit. "
    "No match is not proof that an image is unused."
)
STATUS_MEANINGS = {
    "in_use": "A current published reference was found within this audit's scope.",
    "imported_unconfirmed": "Import evidence is retained; no current reference was found within scope.",
    "existing_unverified": "No current reference or known import mapping was found; usage remains unknown.",
    "new_not_deployed": "The intake's not-deployed state is retained because no positive import/use evidence was found.",
}


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def positive_id(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not an attachment/post ID")
    number = int(value)
    if number <= 0:
        raise ValueError("Attachment/post IDs must be positive")
    return number


def normalize_site(value):
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname:
        raise ValueError("--site must be an absolute HTTP(S) WordPress site URL")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("--site must not contain credentials, a query or a fragment")
    return value.rstrip("/")


def url_key(value, site):
    """Canonical URL identity; keep the host and case-sensitive path."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = html.unescape(value.strip())
    parts = urllib.parse.urlsplit(urllib.parse.urljoin(site + "/", value))
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    path = urllib.parse.unquote(parts.path)
    # Some optimizers append .webp to the original filename; WordPress sizes
    # may combine -scaled and -WIDTHxHEIGHT. The underlying filename is stable.
    path = re.sub(r"(?i)(\.(?:jpe?g|png|gif))\.webp$", r"\1", path)
    while True:
        shorter = re.sub(r"-(?:\d+x\d+|scaled)(?=\.[A-Za-z0-9]+$)", "", path)
        if shorter == path:
            break
        path = shorter
    return parts.netloc.lower(), path


def safe_attached_file(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("An import mapping needs a nonempty attached_file")
    value = value.replace("\\", "/").lstrip("/")
    decoded = urllib.parse.unquote(value)
    if not decoded or "://" in decoded or ".." in PurePosixPath(decoded).parts or "?" in decoded or "#" in decoded:
        raise ValueError("attached_file must be a relative WordPress uploads path")
    return value


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_inventory(data):
    if not isinstance(data, dict) or not isinstance(data.get("images"), list):
        raise ValueError("Inventory must be an object containing an images array")
    keys, ids = set(), set()
    for row in data["images"]:
        if not isinstance(row, dict) or not row.get("key") or not row.get("id") or not row.get("file"):
            raise ValueError("Every inventory image needs existing id, key and file fields")
        if row["key"] in keys or row["id"] in ids:
            raise ValueError("Inventory asset keys and IDs must be unique")
        keys.add(row["key"]); ids.add(row["id"])
        if not isinstance(row.get("usage", {}), dict):
            raise ValueError("Image usage must be an object")
    return {row["key"]: row for row in data["images"]}


def merge_imports(by_key, payload, captured_at):
    """Consume only sanitized attachment_id/catalog_key/attached_file fields."""
    if payload is None:
        return {"supplied_rows": 0, "matched_rows": 0, "unknown_catalog_keys": 0}
    if isinstance(payload, dict):
        payload = payload.get("rows", payload.get("results"))
    if not isinstance(payload, list):
        raise ValueError("--imports must contain an array, or an object with a rows array")
    matched = unknown = 0
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Each import mapping must be an object")
        key = entry.get("catalog_key")
        if key not in by_key:
            unknown += 1
            continue
        aid = positive_id(entry.get("attachment_id"))
        attached_file = safe_attached_file(entry.get("attached_file"))
        usage = by_key[key].setdefault("usage", {})
        usage["attachment_ids"] = sorted({positive_id(x) for x in usage.get("attachment_ids", [])} | {aid})
        records = {positive_id(r["attachment_id"]): dict(r) for r in usage.get("import_records", [])}
        records[aid] = {"attachment_id": aid, "attached_file": attached_file,
                        "mapping_checked_at": captured_at, "evidence": "provided_import_mapping"}
        usage["import_records"] = sorted(records.values(), key=lambda r: r["attachment_id"])
        matched += 1
    return {"supplied_rows": len(payload), "matched_rows": matched, "unknown_catalog_keys": unknown}


def fetch_json(url, timeout):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Supremacy-Artwork-Usage-Audit/1.0",
        "Accept": "application/json", "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(25_000_001)
        if len(body) > 25_000_000:
            raise ValueError("REST response exceeded the audit's size limit")
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return json.loads(body.decode("utf-8")), response.headers


def fetch_published(site, timeout, workers, stamp):
    def page(endpoint, number):
        params = {"per_page": 100, "page": number, "status": "publish",
                  "_fields": "id,title,content,featured_media,link,status", "_usage_audit": stamp}
        rows, headers = fetch_json(site + "/wp-json/wp/v2/" + endpoint + "?" + urllib.parse.urlencode(params), timeout)
        if not isinstance(rows, list):
            raise ValueError("WordPress did not return a public post/page list")
        if headers.get("X-WP-Total") is None or headers.get("X-WP-TotalPages") is None:
            raise ValueError("Missing pagination totals; cannot confirm audit coverage")
        return rows, int(headers["X-WP-Total"]), int(headers["X-WP-TotalPages"])

    endpoints = ("posts", "pages")
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, workers)) as pool:
        first = dict(zip(endpoints, pool.map(lambda endpoint: page(endpoint, 1), endpoints)))
    records = {endpoint: list(first[endpoint][0]) for endpoint in endpoints}
    jobs = [(endpoint, number) for endpoint in endpoints for number in range(2, first[endpoint][2] + 1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(page, *job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            endpoint, number = futures[future]
            rows, total, pages = future.result()
            if (total, pages) != first[endpoint][1:]:
                raise ValueError("Published totals changed during the audit; rerun without writing")
            records[endpoint].extend(rows)
    for endpoint, rows in records.items():
        if len(rows) != first[endpoint][1] or len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Incomplete or repeated REST pagination; inventory was not updated")
        if any(row.get("status") != "publish" for row in rows):
            raise ValueError("Unexpected nonpublished record in public audit")
        rows.sort(key=lambda row: positive_id(row["id"]))
    return records


def fetch_known_media(site, attachment_ids, timeout, workers, stamp):
    """Resolve known IDs only; no library-wide scan and no authentication."""
    ids = sorted(attachment_ids)
    chunks = [ids[start:start + 100] for start in range(0, len(ids), 100)]
    def fetch_chunk(chunk):
        params = {"include": ",".join(map(str, chunk)), "per_page": 100,
                  "_fields": "id,source_url,media_details.sizes", "_usage_audit": stamp}
        data, _ = fetch_json(site + "/wp-json/wp/v2/media?" + urllib.parse.urlencode(params), timeout)
        if not isinstance(data, list):
            raise ValueError("WordPress did not return a public media list")
        return data
    media = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for chunk in pool.map(fetch_chunk, chunks):
            for row in chunk:
                if positive_id(row["id"]) in attachment_ids:
                    media[int(row["id"])] = row
    return media


def build_indexes(rows, media, site):
    by_id, by_url = {}, {}
    def add_url(value, key):
        normalized = url_key(value, site)
        if normalized:
            by_url.setdefault(normalized, set()).add(key)
    for row in rows:
        key, usage = row["key"], row.setdefault("usage", {})
        for value in usage.get("attachment_ids", []):
            by_id.setdefault(positive_id(value), set()).add(key)
        for record in usage.get("import_records", []):
            if record.get("attached_file"):
                add_url(site + "/wp-content/uploads/" + safe_attached_file(record["attached_file"]), key)
    for aid, data in media.items():
        for key in by_id.get(aid, set()):
            add_url(data.get("source_url"), key)
            for size in data.get("media_details", {}).get("sizes", {}).values():
                add_url(size.get("source_url"), key)
    return by_id, by_url


def source_url_index(rows, site, inventory_path):
    """Optional same-site provenance references, never attachment/import evidence.

    Legacy inventory rows may omit original_url. In a repository checkout,
    resolve their exact file/key through their original local catalog instead.
    """
    result, catalogs_read, catalogs_missing = {}, [], []
    row_by_file = {row["file"]: row for row in rows}
    host = urllib.parse.urlsplit(site).netloc.lower()

    def add(value, key):
        normalized = url_key(value, site)
        if normalized and normalized[0] == host and "/wp-content/uploads/" in normalized[1]:
            result.setdefault(normalized, set()).add(key)

    for row in rows:
        for field in ("original_url", "original", "url"):
            add(row.get(field), row["key"])
    groups = sorted({row.get("original_gallery") for row in rows if row.get("original_gallery")})
    for group in groups:
        if not isinstance(group, str) or not re.fullmatch(r"[a-z0-9-]+", group):
            raise ValueError("Invalid local catalog name in inventory")
        path = Path(inventory_path).parent / (group + ".json")
        if not path.is_file():
            catalogs_missing.append(path.name)
            continue
        catalog = load_json(path)
        entries = catalog.get("images", []) if isinstance(catalog, dict) else catalog
        if not isinstance(entries, list):
            raise ValueError("Local source catalog must contain an images array")
        catalogs_read.append(path.name)
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Local source catalog entries must be objects")
            row = row_by_file.get(entry.get("file"))
            if not row or row.get("original_gallery") != group:
                continue
            # Only match the existing canonical key; do not create new rows.
            if hashlib.sha256(entry["file"].encode("utf-8")).hexdigest() != row["key"]:
                continue
            for field in ("original_url", "original", "url"):
                add(entry.get(field), row["key"])
    return result, {"source_catalogs_read": catalogs_read, "source_catalogs_missing": catalogs_missing,
                    "same_site_source_url_identities": len(result)}


class ImageReferences(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.attachment_ids, self.urls = [], []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"img", "source"}:
            for token in (values.get("class") or "").split():
                match = re.fullmatch(r"wp-image-(\d+)", token)
                if match:
                    self.attachment_ids.append(int(match.group(1)))
            for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                if values.get(attr):
                    self.urls.append((values[attr], "content image"))
            for attr in ("srcset", "data-srcset", "data-lazy-srcset"):
                for item in (values.get(attr) or "").split(","):
                    tokens = item.strip().split()
                    if tokens:
                        self.urls.append((tokens[0], "content image"))
        for match in re.finditer(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)''', values.get("style") or "", re.I):
            self.urls.append((next(value for value in match.groups() if value is not None).strip(), "inline background"))


def find_placements(records, by_id, by_url, site, by_source_url=None):
    placements = {}
    ambiguous_urls = set()
    for endpoint, posts in records.items():
        for post in posts:
            found = {}
            def add(keys, kind, evidence):
                for key in keys:
                    item = found.setdefault(key, {"kinds": set(), "matched_by": set()})
                    item["kinds"].add(kind); item["matched_by"].add(evidence)
            featured_id = int(post.get("featured_media") or 0)
            add(by_id.get(featured_id, set()), "featured", "known_attachment_id")
            parser = ImageReferences(post.get("content", {}).get("rendered", ""))
            for aid in parser.attachment_ids:
                add(by_id.get(aid, set()), "content image", "known_attachment_id")
            for url, kind in parser.urls:
                normalized = url_key(url, post.get("link") or site)
                keys = by_url.get(normalized, set())
                if len(keys) == 1:
                    add(keys, kind, "mapped_image_url")
                elif len(keys) > 1:
                    ambiguous_urls.add(normalized)
                source_keys = (by_source_url or {}).get(normalized, set())
                if len(source_keys) == 1:
                    add(source_keys, kind, "original_source_url")
                elif len(source_keys) > 1:
                    ambiguous_urls.add(normalized)
            for key, evidence in found.items():
                placements.setdefault(key, []).append({
                    "post_id": positive_id(post["id"]),
                    "title": html.unescape(post.get("title", {}).get("rendered", "")),
                    "url": post["link"], "kind": ", ".join(sorted(evidence["kinds"])),
                    "post_type": "post" if endpoint == "posts" else "page",
                    "matched_by": sorted(evidence["matched_by"]),
                })
    return placements, len(ambiguous_urls)


def placement_signature(placements):
    return sorted((p.get("post_type", ""), int(p.get("post_id", 0)), p.get("url", ""), p.get("kind", "")) for p in placements)


def apply_usage(data, placements, stamp, site, counts, audit_details):
    transitions = {}
    for row in data["images"]:
        usage = row.setdefault("usage", {})
        old_status = usage.get("status", "")
        previous = copy.deepcopy(usage.get("placements", []))
        current = placements.get(row["key"], [])
        attachments = sorted({positive_id(value) for value in usage.get("attachment_ids", [])})
        if current:
            status = "in_use"
        elif attachments:
            status = "imported_unconfirmed"
        elif old_status == "new_not_deployed" or (not old_status and row.get("origin") == "new"):
            status = "new_not_deployed"
        else:
            status = "existing_unverified"
        if (previous or old_status == "in_use") and (placement_signature(previous) != placement_signature(current) or old_status != status):
            event = {"status": old_status, "checked_at": usage.get("checked_at"),
                     "scope": usage.get("scope"), "placements": previous, "superseded_at": stamp}
            history = usage.setdefault("placement_history", [])
            if not history or any(history[-1].get(k) != event.get(k) for k in ("status", "checked_at", "placements")):
                history.append(event)
        usage.update(status=status, attachment_ids=attachments, placements=current,
                     checked_at=stamp, scope=SCOPE, site=site)
        if old_status != status:
            transition = (old_status or "unset") + " -> " + status
            transitions[transition] = transitions.get(transition, 0) + 1
    data["updated_at"] = stamp
    data["usage_scope"] = SCOPE
    data["usage_audit"] = {"checked_at": stamp, "site": site, "scope": SCOPE,
                           "published_records": counts, **audit_details}
    return transitions


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix="." + path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=Path(__file__).resolve().parent.parent / "image-inventory.json")
    parser.add_argument("--imports", type=Path, help="Optional sanitized import mappings JSON; never a credential file")
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument("--write", action="store_true", help="Atomically replace the local inventory after a complete successful audit")
    parser.add_argument("--report", type=Path, help="Optionally save the audit summary and current placements to a separate file")
    parser.add_argument("--include-source-urls", action="store_true", help="Also match same-site uploads provenance on rows or their local legacy catalogs; does not create import IDs")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.workers <= 8 or args.timeout <= 0:
            raise ValueError("Use 1–8 workers and a positive timeout")
        site = normalize_site(args.site)
        if args.report and args.report.resolve() == args.inventory.resolve():
            raise ValueError("--report must be a different path from the inventory")
        data = load_json(args.inventory)
        by_key = validate_inventory(data)
        known_sites = {row.get("usage", {}).get("site", "").rstrip("/") for row in data["images"] if row.get("usage", {}).get("site")}
        # The initial Supremacy registry predates per-row site fields.
        if not known_sites and data.get("repository") == "Dboss5/supremacy-texas-artwork":
            known_sites.add(DEFAULT_SITE)
        if known_sites and known_sites != {site}:
            raise ValueError("Inventory mappings belong to a different site; use a separate correctly mapped inventory")
        started = utc_now()
        imported = merge_imports(by_key, load_json(args.imports) if args.imports else None, started)
        ids = {positive_id(value) for row in data["images"] for value in row.get("usage", {}).get("attachment_ids", [])}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            posts_future = pool.submit(fetch_published, site, args.timeout, args.workers, started)
            media_future = pool.submit(fetch_known_media, site, ids, args.timeout, args.workers, started)
            records, media = posts_future.result(), media_future.result()
        by_id, by_url = build_indexes(data["images"], media, site)
        source_index, source_details = ({}, {})
        if args.include_source_urls:
            source_index, source_details = source_url_index(data["images"], site, args.inventory)
        placements, ambiguous = find_placements(records, by_id, by_url, site, source_index)
        stamp = utc_now()
        counts = {name: len(rows) for name, rows in records.items()}
        details = {"started_at": started, "known_attachment_ids": len(ids), "public_media_records_returned": len(media),
                   "known_attachment_ids_not_returned": len(ids - set(media)), "ambiguous_url_identities_skipped": ambiguous,
                   "included_source_urls": args.include_source_urls, "import_mapping_refresh": imported,
                   "source_url_only_asset_post_references": sum(p["matched_by"] == ["original_source_url"] for value in placements.values() for p in value),
                   **source_details}
        transitions = apply_usage(data, placements, stamp, site, counts, details)
        status_counts = {status: sum(row["usage"]["status"] == status for row in data["images"]) for status in STATUS_MEANINGS}
        summary = {"mode": "write" if args.write else "dry_run", "inventory_written": False,
                   "checked_at": stamp, "site": site, "scope": SCOPE, "published_records": counts,
                   "inventory_assets": len(data["images"]), "known_imported_assets": sum(bool(row["usage"]["attachment_ids"]) for row in data["images"]),
                   "confirmed_assets": len(placements), "asset_post_references": sum(len(value) for value in placements.values()),
                   "status_counts": status_counts, "status_changes": transitions, "status_meanings": STATUS_MEANINGS, **details}
        if args.write:
            atomic_json(args.inventory, data)
            summary["inventory_written"] = True
        if args.report:
            atomic_json(args.report, {**summary, "placements_by_catalog_key": placements})
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print("Usage audit failed: " + str(error) + ". No WordPress changes were made.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
