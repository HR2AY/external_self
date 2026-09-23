#!/usr/bin/env python3
"""Read-only Internet Archive discovery, inspection, and Wayback normalization."""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import re
import sys
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "ExternalSelf/1.0 (OpenAI Codex; read-only historical research)"
SEARCH_URL = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/{identifier}"
DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"
DETAILS_URL = "https://archive.org/details/{identifier}"
CDX_URL = "https://web.archive.org/cdx/search/cdx"
MAX_RESULTS = 10
CACHE_DIR = Path(tempfile.gettempdir()) / "external-self-ia-cache"
CACHE_TTL_SECONDS = 24 * 60 * 60


def scalar(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def values(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


def compact_text(value: Any, limit: int = 360) -> str | None:
    text = scalar(value)
    if not text:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def request_json(url: str, attempts: int = 1) -> Any:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    try:
        if time.time() - cache_path.stat().st_mtime <= CACHE_TTL_SECONDS:
            return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    delay = 1.0
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                value = json.loads(response.read().decode("utf-8"))
                cache_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                return value
        except urllib.error.HTTPError as error:
            if error.code != 429 and not 500 <= error.code < 600:
                raise
            retry_after = error.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
        except (urllib.error.URLError, TimeoutError):
            wait = delay
        if attempt + 1 == attempts:
            break
        time.sleep(min(wait, 30))
        delay = min(delay * 2, 8)
    raise RuntimeError(f"Internet Archive request failed after {attempts} attempts: {url}")


def canonical_file_url(identifier: str, filename: str) -> str:
    return DOWNLOAD_URL.format(
        identifier=urllib.parse.quote(identifier, safe=""),
        filename=urllib.parse.quote(filename, safe="/"),
    )


def file_kind(file: dict[str, Any]) -> str:
    name = str(file.get("name", "")).lower()
    extension = name.rsplit(".", 1)[-1] if "." in name else ""
    if extension in {"jpg", "jpeg", "png", "gif", "webp"}:
        return "image"
    if extension in {"mp4", "webm", "ogv"}:
        return "video"
    if extension in {"mp3", "ogg", "oga", "flac", "wav", "m4a"}:
        return "audio"
    if extension in {"pdf", "epub", "txt", "djvu"}:
        return "text"
    return "other"


def useful_files(identifier: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for file in files:
        name = scalar(file.get("name"))
        if not name or name.endswith(("_meta.xml", "_files.xml")):
            continue
        kind = file_kind(file)
        if kind == "other":
            continue
        source = scalar(file.get("source")) or "unknown"
        candidates.append({
            "name": name,
            "kind": kind,
            "format": scalar(file.get("format")),
            "source": source,
            "original_file": scalar(file.get("original")),
            "url": canonical_file_url(identifier, name),
        })

    priority = {"image": 0, "video": 1, "audio": 2, "text": 3}
    originals = [item for item in candidates if item["source"] == "original"]
    derivatives = [item for item in candidates if item["source"] != "original"]
    originals.sort(key=lambda item: (priority[item["kind"]], item["name"]))
    derivatives.sort(key=lambda item: (priority[item["kind"]], item["name"]))
    return {
        "originals": originals[:4],
        "presentation_candidates": (derivatives + originals)[:6],
    }


def normalize_item(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    identifier = scalar(metadata.get("identifier")) or scalar(payload.get("metadata", {}).get("identifier"))
    if not identifier:
        raise ValueError("Internet Archive item has no identifier")
    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    restricted = bool(payload.get("is_dark")) or "access-restricted-item" in values(metadata.get("collection"))
    flags = []
    artifact_date = scalar(metadata.get("date"))
    creator = scalar(metadata.get("creator"))
    if not artifact_date:
        flags.append("artifact_date_missing")
    if not creator:
        flags.append("creator_or_publisher_missing")
    if not scalar(metadata.get("licenseurl")) and not scalar(metadata.get("rights")):
        flags.append("rights_status_not_stated")
    if restricted:
        flags.append("access_restricted")
    if scalar(metadata.get("uploader")) and not creator:
        flags.append("uploader_is_not_proof_of_authorship")

    return {
        "identifier": identifier,
        "title": scalar(metadata.get("title")) or identifier,
        "creator_or_publisher": creator,
        "artifact_date": artifact_date,
        "archive_publicdate": scalar(metadata.get("publicdate")),
        "archive_addeddate": scalar(metadata.get("addeddate")),
        "mediatype": scalar(metadata.get("mediatype")),
        "description": compact_text(metadata.get("description")),
        "subjects": values(metadata.get("subject"))[:12],
        "collections": values(metadata.get("collection"))[:12],
        "contributor": values(metadata.get("contributor"))[:6],
        "uploader": scalar(metadata.get("uploader")),
        "language": values(metadata.get("language"))[:6],
        "rights": scalar(metadata.get("rights")),
        "license_url": scalar(metadata.get("licenseurl")),
        "details_url": DETAILS_URL.format(identifier=urllib.parse.quote(identifier, safe="")),
        "files": {"originals": [], "presentation_candidates": []} if restricted else useful_files(identifier, files),
        "provenance_flags": flags,
        "presentation_note": "Label Internet Archive as the archival host unless it created the item; do not use archive upload dates as artifact dates.",
    }


def item_metadata(identifier: str) -> dict[str, Any]:
    url = METADATA_URL.format(identifier=urllib.parse.quote(identifier, safe=""))
    payload = request_json(url)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected metadata response for {identifier}")
    return normalize_item(payload)


def build_query(args: argparse.Namespace) -> str:
    clauses = [args.query.strip()]
    for field in args.field:
        if "=" not in field:
            raise ValueError(f"Field filter must use name=value: {field}")
        name, value = field.split("=", 1)
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            raise ValueError(f"Invalid field name: {name}")
        escaped = value.replace('"', '\\"')
        clauses.append(f'{name}:"{escaped}"')
    if args.from_year or args.to_year:
        start = f"{args.from_year or 1000}-01-01"
        end = f"{args.to_year or 2999}-12-31"
        clauses.append(f"date:[{start} TO {end}]")
    return " AND ".join(f"({clause})" for clause in clauses if clause)


def search(args: argparse.Namespace) -> dict[str, Any]:
    query = build_query(args)
    limit = max(1, min(args.limit, MAX_RESULTS))
    fields = [
        "identifier", "title", "creator", "date", "publicdate", "addeddate",
        "mediatype", "collection", "contributor", "description", "language", "subject",
    ]
    params: list[tuple[str, str]] = [("q", query), ("rows", str(limit)), ("page", "1"), ("output", "json")]
    params.extend(("fl[]", field) for field in fields)
    params.extend(("sort[]", sort) for sort in (args.sort or ["date asc"]))
    payload = request_json(f"{SEARCH_URL}?{urllib.parse.urlencode(params)}")
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    docs = response.get("docs", []) if isinstance(response, dict) else []
    results = []
    for doc in docs[:limit]:
        identifier = scalar(doc.get("identifier")) if isinstance(doc, dict) else None
        if not identifier:
            continue
        artifact_date = scalar(doc.get("date"))
        creator = scalar(doc.get("creator"))
        flags = []
        if not artifact_date:
            flags.append("artifact_date_missing")
        if not creator:
            flags.append("creator_or_publisher_missing")
        flags.append("run_item_before_presenting")
        results.append({
            "identifier": identifier,
            "title": scalar(doc.get("title")) or identifier,
            "creator_or_publisher": creator,
            "artifact_date": artifact_date,
            "archive_publicdate": scalar(doc.get("publicdate")),
            "archive_addeddate": scalar(doc.get("addeddate")),
            "mediatype": scalar(doc.get("mediatype")),
            "description": compact_text(doc.get("description")),
            "subjects": values(doc.get("subject"))[:8],
            "collections": values(doc.get("collection"))[:8],
            "contributor": values(doc.get("contributor"))[:4],
            "details_url": DETAILS_URL.format(identifier=urllib.parse.quote(identifier, safe="")),
            "provenance_flags": flags,
        })
    return {
        "provider": "Internet Archive",
        "source_role": "peer_candidate_source",
        "query": query,
        "num_found": response.get("numFound", len(results)) if isinstance(response, dict) else len(results),
        "results": results,
        "next_step": "Choose only promising candidates, then run the item command for full metadata, files, rights signals, and OCR. Verify the visible artifact or an independent source before presenting a claim.",
    }


def find_ocr(identifier: str, phrase: str, files: list[dict[str, Any]], max_hits: int) -> list[dict[str, Any]]:
    text_files = []
    for file in files:
        name = scalar(file.get("name"))
        if name and (name.endswith("_djvu.txt") or name.endswith("_text.pdf.txt") or name.endswith(".txt")):
            text_files.append(name)
    hits = []
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    for name in text_files[:3]:
        request = urllib.request.Request(canonical_file_url(identifier, name), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                text = response.read(12_000_000).decode("utf-8", errors="replace")
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            continue
        for match in pattern.finditer(text):
            start = max(0, match.start() - 180)
            end = min(len(text), match.end() + 180)
            excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
            hits.append({"file": name, "excerpt": excerpt, "file_url": canonical_file_url(identifier, name)})
            if len(hits) >= max_hits:
                return hits
    return hits


def inspect_item(args: argparse.Namespace) -> dict[str, Any]:
    encoded = urllib.parse.quote(args.identifier, safe="")
    payload = request_json(METADATA_URL.format(identifier=encoded))
    if not isinstance(payload, dict):
        raise ValueError("Unexpected item metadata response")
    result = normalize_item(payload)
    if args.find_text:
        files = payload.get("files") if isinstance(payload.get("files"), list) else []
        result["ocr_hits"] = find_ocr(args.identifier, args.find_text, files, args.max_hits)
        result["ocr_warning"] = "OCR matches are discovery leads; verify the corresponding visible page or issue."
    return {"provider": "Internet Archive", "source_role": "peer_candidate_source", "item": result}


def wayback(args: argparse.Namespace) -> dict[str, Any]:
    params: list[tuple[str, str]] = [
        ("url", args.url),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,mimetype,digest"),
        ("filter", "statuscode:200"),
        ("collapse", "digest"),
        ("limit", str(max(1, min(args.limit, 50)))),
    ]
    if args.from_year:
        params.append(("from", str(args.from_year)))
    if args.to_year:
        params.append(("to", str(args.to_year)))
    payload = request_json(f"{CDX_URL}?{urllib.parse.urlencode(params)}")
    captures = []
    if isinstance(payload, list) and payload:
        headers = payload[0]
        for row in payload[1:]:
            record = dict(zip(headers, row))
            timestamp = record.get("timestamp", "")
            original = record.get("original", args.url)
            record["capture_url"] = f"https://web.archive.org/web/{timestamp}/{original}"
            record["date_warning"] = "Capture time is not the page publication or event date."
            captures.append(record)
    return {
        "provider": "Internet Archive Wayback Machine",
        "source_role": "peer_candidate_source",
        "original_url": args.url,
        "captures": captures,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search item metadata and enrich candidates")
    search_parser.add_argument("query")
    search_parser.add_argument("--field", action="append", default=[], metavar="NAME=VALUE")
    search_parser.add_argument("--from-year", type=int)
    search_parser.add_argument("--to-year", type=int)
    search_parser.add_argument("--sort", action="append")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.set_defaults(handler=search)

    item_parser = subparsers.add_parser("item", help="Inspect one item and optionally search its OCR text")
    item_parser.add_argument("identifier")
    item_parser.add_argument("--find-text")
    item_parser.add_argument("--max-hits", type=int, default=5)
    item_parser.set_defaults(handler=inspect_item)

    wayback_parser = subparsers.add_parser("wayback", help="Find normalized Wayback captures")
    wayback_parser.add_argument("url")
    wayback_parser.add_argument("--from-year", type=int)
    wayback_parser.add_argument("--to-year", type=int)
    wayback_parser.add_argument("--limit", type=int, default=10)
    wayback_parser.set_defaults(handler=wayback)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, urllib.error.HTTPError) as error:
        print(json.dumps({"provider": "Internet Archive", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
