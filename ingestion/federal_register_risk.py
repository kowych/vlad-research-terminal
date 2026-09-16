"""Ingest free primary U.S. policy documents relevant to macro risk.

The Federal Register API is the authoritative publication channel for U.S.
executive actions and Bureau of Industry and Security notices.  This worker
stores only the API's supplied metadata and each document's original URL; it
never fetches the document body.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg


API_URL = "https://www.federalregister.gov/api/v1/documents.json"
QUERIES: tuple[tuple[str, dict[str, str]], ...] = (
    ("executive_orders", {"conditions[presidential_document_type][]": "executive_order"}),
    ("bis_export_controls", {"conditions[agencies][]": "industry-and-security-bureau"}),
)
REQUEST_HEADERS = {"User-Agent": "Muklanovich-Research/0.1 (local evidence ingestion)"}


def published_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(f"{value}T00:00:00+00:00")


def fetch_documents(parameters: dict[str, str]) -> list[dict[str, object]]:
    query = urlencode({"per_page": "100", "order": "newest", **parameters})
    request = Request(f"{API_URL}?{query}", headers=REQUEST_HEADERS)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Federal Register response did not include a results array.")
    return [result for result in results if isinstance(result, dict)]


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from sources where slug = 'federal-register-risk' and active")
            source = cursor.fetchone()
            if not source:
                raise RuntimeError("Source federal-register-risk is not registered. Apply migration 025 first.")
            source_id = source[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()

        try:
            documents: dict[str, dict[str, object]] = {}
            for query_name, parameters in QUERIES:
                for document in fetch_documents(parameters):
                    document_number = document.get("document_number")
                    if not isinstance(document_number, str) or not document_number:
                        continue
                    documents[document_number] = {**document, "risk_query": query_name}

            written = 0
            with connection.cursor() as cursor:
                for document_number, document in documents.items():
                    original_url = document.get("html_url")
                    title = document.get("title")
                    if not isinstance(original_url, str) or not isinstance(title, str):
                        continue
                    publication_date = document.get("publication_date")
                    if not isinstance(publication_date, str):
                        publication_date = None
                    summary = document.get("abstract")
                    if not isinstance(summary, str):
                        summary = None
                    content_hash = hashlib.sha256(f"{original_url}|{title}|{publication_date or ''}".encode()).hexdigest()
                    cursor.execute(
                        """
                        insert into raw_documents (
                          source_id, external_id, original_url, canonical_url, title_raw,
                          summary_raw, language_code, source_published_at, content_hash, raw_payload
                        ) values (%s, %s, %s, %s, %s, %s, 'en', %s, %s, %s::jsonb)
                        on conflict (canonical_url) do nothing
                        returning id
                        """,
                        (
                            source_id,
                            document_number,
                            original_url,
                            original_url,
                            title,
                            summary,
                            published_at(publication_date),
                            content_hash,
                            json.dumps(document),
                        ),
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cursor.execute(
                        """
                        insert into news_articles (raw_document_id, headline, summary, language_code, published_at)
                        values (%s, %s, %s, 'en', %s)
                        """,
                        (row[0], title, summary, published_at(publication_date)),
                    )
                    written += 1
                cursor.execute(
                    """
                    update ingestion_runs
                    set status = 'completed', completed_at = now(), records_read = %s, records_written = %s
                    where id = %s
                    """,
                    (len(documents), written, run_id),
                )
            connection.commit()
            print(f"Federal Register risk monitor: {written} new metadata records from {len(documents)} documents")
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    "update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s",
                    (str(error), run_id),
                )
            connection.commit()
            raise


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
