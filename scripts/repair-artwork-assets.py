#!/usr/bin/env python3
"""Materialize approved artwork manifests and rebuild complete, verified ZIPs.

This script never searches for substitutes or edits the catalog's selections.
Source provenance stays in JSON; generated image files contain no EXIF/IPTC/XMP.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import time
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from PIL import Image, ImageOps

MANIFESTS = (
    "hvac.json", "air-conditioning.json", "plumbing.json", "electrical.json",
    "pest.json", "garage-doors.json", "holiday-lighting.json", "heating.json",
)
ARCHIVES = {
    "garage-door-images.zip": "garage-doors.json",
    "holiday-lighting-images.zip": "holiday-lighting.json",
    "heating-images.zip": "heating.json",
    "hvac-heating-additions.zip": "hvac-heating-additions.json",
}
FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
MAX_BYTES = 30_000_000
Image.MAX_IMAGE_PIXELS = 80_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest(root: Path, name: str) -> list[dict]:
    value = json.loads((root / name).read_text(encoding="utf-8"))
    entries = value.get("images", []) if isinstance(value, dict) else value
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"Empty or malformed image manifest: {name}")
    return entries


def valid_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        raise ValueError(f"Unsafe asset path: {value}")
    if path.suffix.lower() not in FORMATS:
        raise ValueError(f"Unsupported image format: {value}")
    return path.as_posix()


def inspect_image(data: bytes, path: str) -> dict:
    if not 100 <= len(data) <= MAX_BYTES:
        raise ValueError("Image byte size is outside the supported range")
    with Image.open(io.BytesIO(data)) as picture:
        if getattr(picture, "is_animated", False) or getattr(picture, "n_frames", 1) > 1:
            raise ValueError("Animated image excluded")
        if picture.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError(f"Unsupported image content: {picture.format}")
        picture.verify()
    with Image.open(io.BytesIO(data)) as picture:
        picture.load()
        if min(picture.size) < 1:
            raise ValueError("Image has no usable dimensions")
        return {"width": picture.width, "height": picture.height,
                "format": picture.format, "bytes": len(data), "sha256": sha256(data)}


def strip_source_metadata(data: bytes, path: str) -> bytes:
    inspect_image(data, path)
    with Image.open(io.BytesIO(data)) as picture:
        picture = ImageOps.exif_transpose(picture)
        output = io.BytesIO()
        file_format = FORMATS[Path(path).suffix.lower()]
        # Create a fresh image to prevent source metadata from surviving through info.
        mode = "RGBA" if file_format in ("PNG", "WEBP") and "A" in picture.getbands() else "RGB"
        fresh = Image.new(mode, picture.size)
        fresh.paste(picture.convert(mode))
        options = {"quality": 90, "optimize": True} if file_format == "JPEG" else {}
        if file_format == "WEBP":
            options = {"quality": 90, "method": 6}
        fresh.save(output, format=file_format, **options)
        result = output.getvalue()
    inspect_image(result, path)
    return result


def download(url: str) -> tuple[bytes, str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Missing or invalid public source URL")
    # Encode Unicode path/query characters without double-encoding saved percent escapes.
    request_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc,
        urllib.parse.quote(parsed.path, safe="/%:@!$&'()*+,;=-._~"),
        urllib.parse.quote(parsed.query, safe="%=&?/:+@!$'()*;,~-._"), ""))
    request = urllib.request.Request(request_url, headers={
        "User-Agent": "SupremacyArtworkRepair/1.0 (+https://supremacyservice.com)",
        "Accept": "image/webp,image/png,image/jpeg,*/*;q=0.5",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Source image exceeds the size limit")
        return data, response.url


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".artwork-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        Path(name).replace(path)
    finally:
        Path(name).unlink(missing_ok=True)


def restore_verified_seed(root: Path, approved_paths: set[str]) -> int:
    """Recover approved historical stills without relying on expired remote sources."""
    folder = root / ".artwork-recovery"
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file():
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved_sha = "f3bcf27cba89b3bbfd092ed56c14b59aa1cd637cf3859f35ffbf4ca1be382ace"
    if manifest.get("archive_bytes") != 13102527 or manifest.get("archive_sha256") != approved_sha:
        raise ValueError("Recovery manifest differs from the explicitly approved package")
    archive_file = manifest.get("archive_file")
    if archive_file:
        if archive_file != "approved-recovery.zip":
            raise ValueError("Unexpected recovery archive filename")
        raw = (folder / archive_file).read_bytes()
    else:
        encoded = []
        for part in manifest.get("parts", []):
            name = str(part["file"])
            if Path(name).name != name or not name.endswith(".b64"):
                raise ValueError("Unsafe recovery part name")
            data = (folder / name).read_bytes()
            if len(data) != part["length"] or sha256(data) != part["sha256"]:
                raise ValueError(f"Recovery part checksum mismatch: {name}")
            encoded.append(data)
        raw = base64.b64decode(b"".join(encoded), validate=True)
    if len(raw) != manifest["archive_bytes"] or sha256(raw) != manifest["archive_sha256"]:
        raise ValueError("Recovery archive checksum mismatch")
    expected = {valid_path(item["file"]): item for item in manifest["images"]}
    if len(expected) != 172 or len(manifest["images"]) != 172 or not set(expected).issubset(approved_paths):
        raise ValueError("Recovery includes an image outside the approved catalogs")
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        if set(bundle.namelist()) != set(expected) or bundle.testzip():
            raise ValueError("Recovery archive membership or CRC verification failed")
        checked = {}
        for path, item in expected.items():
            data = bundle.read(path)
            if len(data) != item["bytes"] or sha256(data) != item["sha256"]:
                raise ValueError(f"Recovery image checksum mismatch: {path}")
            inspect_image(data, path)
            checked[path] = data
        for path, data in checked.items():
            atomic_write(root / path, data)
    provenance = {key: manifest[key] for key in ("version", "description", "archive_sha256", "images")}
    atomic_write(root / "asset-recovery-provenance.json", (json.dumps(provenance, indent=2, ensure_ascii=False) + "\n").encode())
    for part in manifest.get("parts", []):
        (folder / part["file"]).unlink(missing_ok=True)
    if archive_file:
        (folder / archive_file).unlink()
    manifest_path.unlink()
    folder.rmdir()
    print(f"Recovered {len(expected)} verified historical still images", flush=True)
    return len(expected)


def materialize(root: Path, entry: dict, verify_only: bool = False) -> dict:
    relative = valid_path(str(entry.get("file", "")))
    path = root / relative
    existing_error = None
    if path.is_file():
        try:
            details = inspect_image(path.read_bytes(), relative)
            return {"file": relative, "status": "verified_existing", **details}
        except Exception as error:
            existing_error = str(error)
    source = str(entry.get("original_url") or entry.get("original") or entry.get("url") or "")
    if verify_only:
        return {"file": relative, "status": "unavailable", "source_url": source,
                "error": existing_error or "Missing file"}
    for attempt in range(3):
        try:
            raw, final_url = download(source)
            cleaned = strip_source_metadata(raw, relative)
            atomic_write(path, cleaned)
            return {"file": relative, "status": "downloaded", "source_url": source,
                    "download_url": final_url, "source_sha256": sha256(raw),
                    **inspect_image(cleaned, relative)}
        except Exception as error:
            last_error = f"{type(error).__name__}: {error}"
            # Retry transient failures; do not try alternate images or bypass access checks.
            if isinstance(error, urllib.error.HTTPError) and error.code in (400, 401, 403, 404, 410):
                break
            if attempt < 2:
                time.sleep(attempt + 1)
    return {"file": relative, "status": "unavailable", "source_url": source, "error": last_error}


def build_archive(root: Path, filename: str, manifest: str, results: dict[str, dict]) -> dict:
    entries = read_manifest(root, manifest)
    paths = sorted({valid_path(str(entry["file"])) for entry in entries})
    missing = [path for path in paths if results.get(path, {}).get("status") == "unavailable" or not (root / path).is_file()]
    if missing:
        return {"file": filename, "status": "incomplete", "expected_images": len(paths),
                "missing_images": missing, "error": "No complete replacement archive published"}
    target = root / filename
    temporary = target.with_suffix(".zip.tmp")
    checksums = {path: sha256((root / path).read_bytes()) for path in paths}
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in paths:
                bundle.write(root / path, path)
            bundle.write(root / manifest, manifest)
            bundle.writestr("SHA256SUMS.txt", "".join(f"{digest}  {path}\n" for path, digest in checksums.items()))
        with zipfile.ZipFile(temporary) as bundle:
            bad = bundle.testzip()
            if bad:
                raise ValueError(f"Archive checksum failure: {bad}")
            actual = {name for name in bundle.namelist() if name in checksums}
            if actual != set(paths):
                raise ValueError("Archive image membership is incomplete")
            for path in paths:
                if sha256(bundle.read(path)) != checksums[path]:
                    raise ValueError(f"Archive image differs from repository file: {path}")
        temporary.replace(target)
        raw = target.read_bytes()
        return {"file": filename, "status": "complete", "image_count": len(paths),
                "bytes": len(raw), "sha256": sha256(raw)}
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    entries: dict[str, dict] = {}
    manifest_counts = {}
    for name in dict.fromkeys((*MANIFESTS, *ARCHIVES.values())):
        items = read_manifest(root, name)
        manifest_counts[name] = len(items)
        for item in items:
            path = valid_path(str(item.get("file", "")))
            entries.setdefault(path, item)
    recovered_count = restore_verified_seed(root, set(entries)) if not args.verify_only else 0
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(24, args.workers))) as pool:
        future_paths = {pool.submit(materialize, root, entry, args.verify_only): path for path, entry in entries.items()}
        for index, future in enumerate(concurrent.futures.as_completed(future_paths), 1):
            path = future_paths[future]
            try:
                results[path] = future.result()
            except Exception as error:
                results[path] = {"file": path, "status": "unavailable", "error": f"{type(error).__name__}: {error}"}
            if index % 25 == 0 or index == len(entries):
                missing = sum(value["status"] == "unavailable" for value in results.values())
                print(f"Checked {index}/{len(entries)} images; {missing} unavailable", flush=True)
    archives = []
    for name, manifest in ARCHIVES.items():
        if args.verify_only:
            try:
                with zipfile.ZipFile(root / name) as bundle:
                    bad = bundle.testzip()
                    if bad:
                        raise ValueError(f"Corrupt entry: {bad}")
                archives.append({"file": name, "status": "verified"})
            except Exception as error:
                archives.append({"file": name, "status": "invalid", "error": str(error)})
        else:
            archives.append(build_archive(root, name, manifest, results))
    counts = {status: sum(item["status"] == status for item in results.values())
              for status in ("verified_existing", "downloaded", "unavailable")}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Approved repository manifests only; no substitute images",
        "manifest_counts": manifest_counts,
        "unique_asset_paths": len(entries), "counts": counts,
        "recovered_from_verified_history": recovered_count,
        "complete": counts["unavailable"] == 0 and all(item["status"] in ("complete", "verified") for item in archives),
        "archives": archives, "images": [results[path] for path in sorted(results)],
    }
    atomic_write(root / "asset-repair-report.json", (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
    print(json.dumps({key: report[key] for key in ("unique_asset_paths", "counts", "complete", "archives")}, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
