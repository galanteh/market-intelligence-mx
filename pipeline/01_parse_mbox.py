#!/usr/bin/env python3
"""
pipeline/01_parse_mbox.py
Converts mbox/Whitepaper.mbox → brief_year_md/Whitepaper_<year>.md

Skips conversion if all markdown files are newer than the mbox.
Returns the number of emails processed.
"""
import mailbox, re, os, sys, email.header
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

BASE     = Path(__file__).resolve().parents[1]
MBOX_PATH = BASE / "mbox" / "Whitepaper.mbox"
MD_DIR    = BASE / "brief_year_md"


def decode_header(value: str) -> str:
    parts = email.header.decode_header(value or "")
    decoded = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(chunk)
    return " ".join(decoded)


def strip_html(html: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def get_text(msg) -> str:
    """Extract plaintext body from email, preferring text/plain."""
    best_plain = ""
    best_html  = ""
    for part in msg.walk():
        ct = part.get_content_type()
        if ct == "text/plain":
            charset = part.get_content_charset() or "utf-8"
            try:
                best_plain = part.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                pass
        elif ct == "text/html" and not best_plain:
            charset = part.get_content_charset() or "utf-8"
            try:
                best_html = part.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                pass
    return best_plain or strip_html(best_html)


def is_fresh() -> bool:
    """Return True if markdown files are newer than the mbox file."""
    if not MBOX_PATH.exists():
        return True   # nothing to parse
    mbox_mtime = MBOX_PATH.stat().st_mtime
    md_files   = list(MD_DIR.glob("Whitepaper_*.md"))
    if not md_files:
        return False
    return all(f.stat().st_mtime >= mbox_mtime for f in md_files)


def run(force: bool = False) -> int:
    if not MBOX_PATH.exists():
        print(f"[01_parse_mbox] ⚠ Mbox not found at {MBOX_PATH} — skipping.")
        return 0

    if not force and is_fresh():
        md_files = list(MD_DIR.glob("Whitepaper_*.md"))
        print(f"[01_parse_mbox] Markdown files are up-to-date ({len(md_files)} files) — skipping.")
        return 0

    MD_DIR.mkdir(parents=True, exist_ok=True)
    by_year: dict[int, list[str]] = {}

    mbox = mailbox.mbox(str(MBOX_PATH))
    total = 0

    for msg in mbox:
        try:
            date_str = msg.get("Date", "")
            try:
                dt = parsedate_to_datetime(date_str)
            except Exception:
                continue
            year = dt.year
            subject = decode_header(msg.get("Subject", "(sin asunto)"))
            body    = get_text(msg)
            if not body.strip():
                continue

            date_fmt = dt.strftime("%d %b %Y")
            entry = f"**Date:** {date_fmt}\n**From:** whitepaper.mx\n\n# {subject}\n\n{body.strip()}\n\n---\n\n"
            by_year.setdefault(year, []).append(entry)
            total += 1
        except Exception:
            continue

    for year, entries in sorted(by_year.items()):
        out_path = MD_DIR / f"Whitepaper_{year}.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("".join(entries))
        print(f"[01_parse_mbox]   {out_path.name}  ({len(entries)} emails)")

    print(f"[01_parse_mbox] ✓ {total} emails → {len(by_year)} archivos Markdown")
    return total


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
