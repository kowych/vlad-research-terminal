"""Ingest publisher-provided RSS metadata without fetching article pages."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import psycopg


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.lower().startswith("utm_")])
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/") or "/", query, ""))


def plain_text(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip() or None


def published_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
            return parsed if parsed and parsed.tzinfo else parsed.replace(tzinfo=timezone.utc) if parsed else datetime.now(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def feed_items(url: str) -> list[dict[str, str | None]]:
    request = Request(url, headers={"User-Agent": "Muklanovich-Research/0.1 (local evidence ingestion)"})
    with urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())
    items = root.findall("./channel/item")
    rss10 = "{http://purl.org/rss/1.0/}"
    dc = "{http://purl.org/dc/elements/1.1/}"
    rdf = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    rdf_items = root.findall(f"{rss10}item")
    if rdf_items:
        return [{
            "guid": item.attrib.get(f"{rdf}about") or item.findtext(f"{rss10}link"),
            "link": item.findtext(f"{rss10}link"),
            "title": item.findtext(f"{rss10}title"),
            "description": item.findtext(f"{rss10}description"),
            "pub_date": item.findtext(f"{dc}date"),
        } for item in rdf_items]
    if not items and root.tag == "{http://www.w3.org/2005/Atom}feed":
        atom = "{http://www.w3.org/2005/Atom}"
        entries = root.findall(f"{atom}entry")
        if not entries:
            raise RuntimeError(f"No Atom entries found: {url}")
        return [{
            "guid": entry.findtext(f"{atom}id"),
            "link": next((link.attrib.get("href") for link in entry.findall(f"{atom}link") if link.attrib.get("rel", "alternate") == "alternate"), None),
            "title": entry.findtext(f"{atom}title"),
            "description": entry.findtext(f"{atom}summary") or entry.findtext(f"{atom}content"),
            "pub_date": entry.findtext(f"{atom}published") or entry.findtext(f"{atom}updated"),
        } for entry in entries]
    if not items:
        raise RuntimeError(f"No RSS or Atom items found: {url}")
    return [{
        "guid": item.findtext("guid"), "link": item.findtext("link"), "title": item.findtext("title"),
        "description": item.findtext("description"), "pub_date": item.findtext("pubDate"),
    } for item in items]


def run(database_url: str, feed_slug: str | None) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            feed_query = """
              select news_feeds.id, sources.id, news_feeds.name, news_feeds.feed_url
              from news_feeds join sources on sources.id = news_feeds.source_id
              where news_feeds.active
              order by news_feeds.name
            """
            if feed_slug:
                feed_query = feed_query.replace("where news_feeds.active", "where news_feeds.active and sources.slug = %s")
                cursor.execute(feed_query, (feed_slug,))
            else:
                cursor.execute(feed_query)
            feeds = cursor.fetchall()
        if not feeds:
            raise RuntimeError("No active news feeds matched")
        for feed_id, source_id, name, url in feeds:
            with connection.cursor() as cursor:
                cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
                run_id = cursor.fetchone()[0]
            connection.commit()
            try:
                items = feed_items(url)
                written = 0
                with connection.cursor() as cursor:
                    for item in items:
                        original_url = item["link"]
                        if not original_url or not item["title"]:
                            continue
                        canonical_url = canonicalize_url(original_url)
                        item_hash = hashlib.sha256(f"{canonical_url}|{item['title']}|{item['pub_date'] or ''}".encode()).hexdigest()
                        cursor.execute("""
                          insert into raw_documents (source_id, feed_id, external_id, original_url, canonical_url, title_raw, summary_raw, language_code, source_published_at, content_hash, raw_payload)
                          values (%s, %s, %s, %s, %s, %s, %s, 'en', %s, %s, %s::jsonb)
                          on conflict (canonical_url) do nothing returning id
                        """, (source_id, feed_id, item["guid"] or canonical_url, original_url, canonical_url, plain_text(item["title"]), plain_text(item["description"]), published_at(item["pub_date"]), item_hash, json.dumps(item)))
                        row = cursor.fetchone()
                        if not row:
                            continue
                        cursor.execute("""
                          insert into news_articles (raw_document_id, headline, summary, language_code, published_at)
                          values (%s, %s, %s, 'en', %s)
                        """, (row[0], plain_text(item["title"]), plain_text(item["description"]), published_at(item["pub_date"])))
                        written += 1
                    cursor.execute("update news_feeds set last_checked_at = now() where id = %s", (feed_id,))
                    cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(items), written, run_id))
                connection.commit()
                print(f"{name}: {written} new metadata records")
            except Exception as error:
                connection.rollback()
                with connection.cursor() as cursor:
                    cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
                connection.commit()
                # One publisher's WAF or malformed XML must not suppress every
                # other source in a scheduled run. The failed run remains
                # visible in PostgreSQL for monitoring and remediation.
                print(f"{name}: failed ({error})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="Only ingest one source slug")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.source)
