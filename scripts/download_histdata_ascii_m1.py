#!/usr/bin/env python3
"""Descarga y organiza el catalogo ASCII M1 de HistData."""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar
import zipfile
from pathlib import Path


BASE_URL = "https://www.histdata.com"
PAIR_LIST_URL = f"{BASE_URL}/download-free-forex-data/?/ascii/1-minute-bar-quotes"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HistDataAsciiDownloader/1.0"

PAIR_LINK_RE = re.compile(
    r'href="(?P<href>/download-free-forex-historical-data/\?/ascii/1-minute-bar-quotes/(?P<pair>[A-Z0-9]+))"[^>]*>'
    r"<strong>(?P<display>[^<]+)</strong></a><br/>\((?P<start>[^)]+)\)",
    re.IGNORECASE,
)
ENTRY_LINK_RE = re.compile(
    r'href="(?P<href>/download-free-forex-historical-data/\?/ascii/1-minute-bar-quotes/(?P<pair>[a-z0-9]+)/(?P<year>\d{4})(?:/(?P<month>\d{1,2}))?)"[^>]*>'
    r"<strong>(?P<label>[^<]+)</strong></a>",
    re.IGNORECASE,
)
FORM_RE_TEMPLATE = r'<form id="{form_id}".*?action="(?P<action>[^"]+)".*?>(?P<body>.*?)</form>'
INPUT_RE = re.compile(r'<input[^>]+name="(?P<name>[^"]+)"[^>]+value="(?P<value>[^"]*)"')
DOWNLOAD_NAME_RE = re.compile(r'<a id="a_file"[^>]*>(?P<name>[^<]+)</a>')
STATUS_NAME_RE = re.compile(r'<a id="a_status"[^>]*>(?P<name>[^<]+)</a>')

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


@dataclasses.dataclass
class PairInfo:
    order: int
    code: str
    display: str
    start_label: str
    href: str


@dataclasses.dataclass
class EntryInfo:
    pair_code: str
    year: int
    month: int | None
    label: str
    href: str

    @property
    def kind(self) -> str:
        return "month" if self.month is not None else "year"


class HistDataClient:
    def __init__(self, sleep_seconds: float = 0.15, timeout: int = 60):
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.last_request_at = 0.0

    def _throttle(self) -> None:
        elapsed = time.time() - self.last_request_at
        if elapsed < self.sleep_seconds:
            time.sleep(self.sleep_seconds - elapsed)

    def request(self, url: str, data: dict[str, str] | None = None, referer: str | None = None) -> bytes:
        self._throttle()
        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer
        encoded = None
        if data is not None:
            encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers=headers)
        with self.opener.open(req, timeout=self.timeout) as resp:
            payload = resp.read()
        self.last_request_at = time.time()
        return payload

    def get_text(self, url: str) -> str:
        return self.request(url).decode("utf-8", errors="replace")

    def post_bytes(self, url: str, data: dict[str, str], referer: str) -> bytes:
        return self.request(url, data=data, referer=referer)


def parse_pairs(page_html: str) -> list[PairInfo]:
    pairs: list[PairInfo] = []
    for idx, match in enumerate(PAIR_LINK_RE.finditer(page_html), start=1):
        pairs.append(
            PairInfo(
                order=idx,
                code=match.group("pair").upper(),
                display=html.unescape(match.group("display")),
                start_label=html.unescape(match.group("start")),
                href=match.group("href"),
            )
        )
    return pairs


def parse_entries(page_html: str) -> list[EntryInfo]:
    entries: list[EntryInfo] = []
    seen: set[str] = set()
    for match in ENTRY_LINK_RE.finditer(page_html):
        href = match.group("href")
        if href in seen:
            continue
        seen.add(href)
        month = match.group("month")
        entries.append(
            EntryInfo(
                pair_code=match.group("pair").upper(),
                year=int(match.group("year")),
                month=int(month) if month else None,
                label=html.unescape(match.group("label")),
                href=href,
            )
        )
    return entries


def parse_download_form(page_html: str) -> dict[str, object]:
    download_name_match = DOWNLOAD_NAME_RE.search(page_html)
    status_name_match = STATUS_NAME_RE.search(page_html)
    if not download_name_match:
        raise RuntimeError("No se encontro el nombre del ZIP en la pagina final de HistData.")

    result: dict[str, object] = {
        "download_name": html.unescape(download_name_match.group("name")).strip(),
        "status_name": html.unescape(status_name_match.group("name")).strip() if status_name_match else None,
    }

    for form_id, key in (("file_down", "download"), ("file_status", "status")):
        form_match = re.search(FORM_RE_TEMPLATE.format(form_id=form_id), page_html, re.IGNORECASE | re.DOTALL)
        if not form_match:
            continue
        fields = {m.group("name"): html.unescape(m.group("value")) for m in INPUT_RE.finditer(form_match.group("body"))}
        result[key] = {
            "action": urllib.parse.urljoin(BASE_URL, form_match.group("action")),
            "fields": fields,
        }
    if "download" not in result:
        raise RuntimeError("No se encontro el formulario de descarga en la pagina final de HistData.")
    return result


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())


def pair_root(base_dir: Path, pair: PairInfo) -> Path:
    return base_dir / f"{pair.order:02d}_{pair.code}"


def entry_root(base_dir: Path, pair: PairInfo, entry: EntryInfo) -> Path:
    root = pair_root(base_dir, pair) / str(entry.year)
    if entry.month is None:
        return root / "full_year"
    month_name = MONTH_NAMES.get(entry.month, f"month_{entry.month:02d}")
    return root / "months" / f"{entry.month:02d}_{month_name}"


def save_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_inventory(client: HistDataClient, pair_limit: int | None = None, pair_codes: set[str] | None = None) -> tuple[list[PairInfo], dict[str, list[EntryInfo]]]:
    root_html = client.get_text(PAIR_LIST_URL)
    pairs = parse_pairs(root_html)
    if pair_codes:
        pairs = [pair for pair in pairs if pair.code in pair_codes]
    if pair_limit is not None:
        pairs = pairs[:pair_limit]

    entries_by_pair: dict[str, list[EntryInfo]] = {}
    for pair in pairs:
        pair_html = client.get_text(urllib.parse.urljoin(BASE_URL, pair.href))
        entries_by_pair[pair.code] = parse_entries(pair_html)
        print(f"[inventario] {pair.code}: {len(entries_by_pair[pair.code])} entradas", flush=True)

    return pairs, entries_by_pair


def download_entry(
    client: HistDataClient,
    base_dir: Path,
    pair: PairInfo,
    entry: EntryInfo,
    extract_zip: bool,
    overwrite: bool,
) -> None:
    target_dir = ensure_dir(entry_root(base_dir, pair, entry))
    final_url = urllib.parse.urljoin(BASE_URL, entry.href)
    final_html = client.get_text(final_url)
    payload = parse_download_form(final_html)

    zip_name = sanitize_name(str(payload["download_name"]))
    status_name = sanitize_name(str(payload["status_name"])) if payload.get("status_name") else None
    zip_path = target_dir / zip_name
    status_path = target_dir / status_name if status_name else None
    extracted_dir = target_dir / "extracted"

    if not overwrite and zip_path.exists() and zip_path.stat().st_size > 0 and (not extract_zip or extracted_dir.exists()):
        print(f"[skip] {pair.code} {entry.label}", flush=True)
        return

    download_meta = payload["download"]
    zip_bytes = client.post_bytes(
        url=str(download_meta["action"]),
        data=dict(download_meta["fields"]),
        referer=final_url,
    )
    if not zip_bytes:
        raise RuntimeError(f"HistData devolvio un ZIP vacio para {pair.code} {entry.label}.")
    zip_path.write_bytes(zip_bytes)

    status_meta = payload.get("status")
    if status_meta and status_path is not None:
        status_bytes = client.post_bytes(
            url=str(status_meta["action"]),
            data=dict(status_meta["fields"]),
            referer=final_url,
        )
        status_path.write_bytes(status_bytes)

    if extract_zip:
        ensure_dir(extracted_dir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extracted_dir)

    metadata = {
        "pair_code": pair.code,
        "pair_display": pair.display,
        "order": pair.order,
        "entry_kind": entry.kind,
        "year": entry.year,
        "month": entry.month,
        "label": entry.label,
        "source_page": final_url,
        "zip_file": zip_name,
        "status_file": status_name,
    }
    save_json(target_dir / "_entry.json", metadata)
    print(f"[ok] {pair.code} {entry.label} -> {zip_path.name}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga y organiza el catalogo Generic ASCII M1 de HistData.")
    parser.add_argument("--root", type=Path, default=Path("data") / "histdata_ascii_m1", help="Carpeta raiz de destino.")
    parser.add_argument("--pair-limit", type=int, default=None, help="Limita el numero de pares a procesar.")
    parser.add_argument("--entry-limit-per-pair", type=int, default=None, help="Limita el numero de entradas por par.")
    parser.add_argument("--pairs", type=str, default="", help="Lista separada por comas de pares concretos, por ejemplo EURUSD,GBPUSD.")
    parser.add_argument("--inventory-only", action="store_true", help="Solo genera el inventario, sin descargar ZIPs.")
    parser.add_argument("--no-extract", action="store_true", help="No extrae los ZIP descargados.")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescribe archivos ya existentes.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Pausa minima entre peticiones HTTP.")
    args = parser.parse_args()

    pair_codes = {item.strip().upper() for item in args.pairs.split(",") if item.strip()} or None
    root_dir = args.root.resolve()
    ensure_dir(root_dir)

    client = HistDataClient(sleep_seconds=args.sleep)
    pairs, entries_by_pair = build_inventory(client, pair_limit=args.pair_limit, pair_codes=pair_codes)

    inventory_payload = {
        "source": PAIR_LIST_URL,
        "generated_at_unix": int(time.time()),
        "pair_count": len(pairs),
        "pairs": [
            {
                "order": pair.order,
                "code": pair.code,
                "display": pair.display,
                "start_label": pair.start_label,
                "entry_count": len(entries_by_pair[pair.code]),
            }
            for pair in pairs
        ],
    }
    save_json(root_dir / "_inventory.json", inventory_payload)

    for pair in pairs:
        pair_dir = ensure_dir(pair_root(root_dir, pair))
        pair_entries = entries_by_pair[pair.code]
        if args.entry_limit_per_pair is not None:
            pair_entries = pair_entries[: args.entry_limit_per_pair]

        pair_payload = {
            "order": pair.order,
            "code": pair.code,
            "display": pair.display,
            "start_label": pair.start_label,
            "entries": [dataclasses.asdict(entry) | {"kind": entry.kind} for entry in pair_entries],
        }
        save_json(pair_dir / "_pair.json", pair_payload)

        if args.inventory_only:
            continue

        for entry in pair_entries:
            download_entry(
                client=client,
                base_dir=root_dir,
                pair=pair,
                entry=entry,
                extract_zip=not args.no_extract,
                overwrite=args.overwrite,
            )

    print(f"Inventario guardado en: {root_dir / '_inventory.json'}", flush=True)
    if not args.inventory_only:
        print(f"Descargas organizadas en: {root_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
