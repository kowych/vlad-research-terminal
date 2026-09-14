"""Classify publisher metadata into explainable, market-aware evidence events.

The rules deliberately produce hypotheses (expected direction and transmission),
not facts about a realised price move. Measured reactions are stored later in
``news_event_market_reactions`` with their own provenance.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass

import psycopg


COUNTRY_TERMS: dict[str, tuple[str, ...]] = {
    "US": ("federal reserve", "fomc", "united states", "u.s.", "white house", "trump"),
    "IR": ("iran", "iranian", "tehran", "strait of hormuz"),
    "GB": ("united kingdom", "u.k.", "britain", "british"),
    "FR": ("france", "french", "euro area", "eurosystem"),
    "DE": ("germany", "german", "euro area", "eurosystem"),
    "UA": ("ukraine", "ukrainian", "kyiv", "kiev"),
    "RU": ("russia", "russian", "moscow", "kremlin"),
    "AU": ("australia", "australian"), "CA": ("canada", "canadian"),
    "NZ": ("new zealand", "new zealand's"), "CN": ("china", "chinese", "beijing"),
    "JP": ("japan", "japanese", "tokyo"), "IT": ("italy", "italian"),
    "ES": ("spain", "spanish"), "CH": ("switzerland", "swiss"),
    "NO": ("norway", "norwegian"), "SE": ("sweden", "swedish"),
    "TR": ("turkey", "turkish", "türkiye"), "IN": ("india", "indian"),
    "KR": ("south korea", "korea", "korean", "seoul"), "PL": ("poland", "polish", "zloty"),
}

TOPIC_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("policy-rate", ("interest rate", "monetary policy", "deposit facility", "refinancing operations", "fomc"), "macro_release"),
    ("core-cpi", ("core inflation", "underlying inflation"), "macro_release"),
    ("cpi", ("inflation", "consumer price", "hicp", "cpi"), "macro_release"),
    ("unemployment-rate", ("unemployment", "labour market", "labor market", "employment"), "macro_release"),
    ("real-gdp-growth", ("gross domestic product", "gdp", "economic growth"), "macro_release"),
    ("sovereign-10y", ("government bond", "sovereign yield", "yield curve", "bond yield"), "market_reaction"),
)
CONFLICT_TERMS = ("war", "conflict", "attack", "strike", "military", "missile", "sanction", "blockade", "hormuz")
CHINA_TECH_TERMS = ("semiconductor", "chip", "artificial intelligence", "ai", "export control", "technology")
SOURCE_COUNTRIES = {
    "federal-reserve-board": ("US",),
    "ecb-communications": ("DE", "FR", "IT", "ES"),
    "bank-of-canada-communications": ("CA",),
    "reserve-bank-australia-communications": ("AU",),
}


@dataclass(frozen=True)
class CountryImpact:
    iso2: str
    scope: str = "direct"
    confidence: str = "medium"
    note: str | None = None


@dataclass(frozen=True)
class Entity:
    slug: str
    name: str
    entity_type: str
    country_iso2: str | None
    role: str


@dataclass(frozen=True)
class MarketImpact:
    instrument: str
    scope: str
    direction: str
    confidence: str
    note: str


def matches(text: str, terms: Iterable[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) for term in terms)


def classify(article: dict[str, str]) -> tuple[list[CountryImpact], list[str], str, int, list[Entity], list[MarketImpact]]:
    text = f"{article['headline']} {article.get('summary') or ''}".lower()
    direct = [iso2 for iso2, terms in COUNTRY_TERMS.items() if matches(text, terms)]
    source_slug = article["source_slug"]
    direct = list(dict.fromkeys([*direct, *SOURCE_COUNTRIES.get(source_slug, ())]))

    countries = [CountryImpact(iso2) for iso2 in direct]
    topics = [(slug, event_type) for slug, terms, event_type in TOPIC_RULES if matches(text, terms)]
    indicators = [slug for slug, _ in topics]
    event_type = topics[0][1] if topics else "official_communication"
    entities: list[Entity] = []
    impacts: list[MarketImpact] = []

    if source_slug == "federal-reserve-board":
        entities.append(Entity("federal-reserve", "Federal Reserve", "institution", "US", "policy_maker"))
    if source_slug == "ecb-communications":
        entities.append(Entity("european-central-bank", "European Central Bank", "institution", None, "policy_maker"))
    if matches(text, ("trump", "white house")):
        entities.extend((Entity("donald-trump", "Donald Trump", "person", "US", "actor"), Entity("us-administration", "United States administration", "government", "US", "policy_maker")))
        event_type = "policy_politics"
        impacts.append(MarketImpact("us-10y", "direct", "ambiguous", "low", "Policy communication requires market confirmation."))

    iran_conflict = matches(text, ("iran", "iranian", "hormuz")) and matches(text, CONFLICT_TERMS)
    if iran_conflict:
        event_type = "geopolitics_conflict"
        entities.append(Entity("iran-conflict", "Iran-related conflict", "conflict", "IR", "subject"))
        countries.extend((CountryImpact("CN", "spillover", "medium", "Oil-import exposure."), CountryImpact("RU", "spillover", "low", "Energy-market transmission.")))
        impacts.extend((MarketImpact("brent-crude", "direct", "up", "medium", "Supply and shipping-risk transmission."), MarketImpact("wti-crude", "spillover", "up", "medium", "Global oil-price transmission.")))

    ukraine_conflict = matches(text, ("ukraine", "ukrainian", "kyiv", "kiev", "russia", "russian")) and matches(text, CONFLICT_TERMS)
    if ukraine_conflict:
        event_type = "geopolitics_conflict"
        entities.append(Entity("russia-ukraine-war", "Russia–Ukraine war", "conflict", "UA", "subject"))
        countries.extend((CountryImpact("PL", "regional", "high", "Direct regional security and trade exposure."), CountryImpact("DE", "spillover", "medium", "European energy and industrial exposure."), CountryImpact("FR", "spillover", "medium", "European risk and policy transmission.")))
        impacts.extend((MarketImpact("ttf-natural-gas", "spillover", "up", "medium", "European gas-supply risk."), MarketImpact("brent-crude", "spillover", "ambiguous", "low", "Energy-risk premium depends on disruption.")))

    china_tech = matches(text, ("china", "chinese", "beijing")) and matches(text, CHINA_TECH_TERMS)
    if china_tech:
        event_type = "technology_industrial_policy"
        entities.append(Entity("china-technology-policy", "China technology policy", "technology", "CN", "subject"))
        countries.extend((CountryImpact("US", "spillover", "medium", "Supply-chain and export-control transmission."), CountryImpact("JP", "spillover", "medium", "Semiconductor equipment exposure."), CountryImpact("KR", "spillover", "medium", "Semiconductor supply-chain exposure.")))
        impacts.extend((MarketImpact("semiconductor-index", "spillover", "ambiguous", "medium", "Technology-policy and supply-chain transmission."), MarketImpact("msci-china", "direct", "ambiguous", "medium", "Domestic technology-sector sensitivity."), MarketImpact("usd-cny", "direct", "ambiguous", "low", "Policy and risk-sentiment channel.")))

    scope_rank = {"direct": 3, "regional": 2, "spillover": 1}
    unique_countries: dict[str, CountryImpact] = {}
    for country in countries:
        current = unique_countries.get(country.iso2)
        if current is None or scope_rank[country.scope] > scope_rank[current.scope]:
            unique_countries[country.iso2] = country
    materiality = 5 if event_type == "geopolitics_conflict" else 4 if event_type in {"policy_politics", "technology_industrial_policy", "macro_release"} else 3 if direct else 2
    return list(unique_countries.values()), indicators, event_type, materiality, entities, impacts


def source_score(source_slug: str) -> int:
    return 5 if source_slug in {"federal-reserve-board", "ecb-communications", "bank-of-canada-communications", "reserve-bank-australia-communications"} else 2 if source_slug == "gdelt-discovery" else 3


def upsert_entity(cursor: psycopg.Cursor, entity: Entity, country_ids: dict[str, str]) -> str:
    cursor.execute("""insert into news_entities (slug, name, entity_type, country_id) values (%s, %s, %s, %s) on conflict (slug) do update set name = excluded.name returning id::text""", (entity.slug, entity.name, entity.entity_type, country_ids.get(entity.country_iso2 or "")))
    return cursor.fetchone()[0]


def enrich_event(cursor: psycopg.Cursor, event_id: str, article: dict[str, str], country_ids: dict[str, str], indicator_ids: dict[str, str], instrument_ids: dict[str, str]) -> None:
    countries, indicators, event_type, materiality, entities, impacts = classify(article)
    cursor.execute("update news_event_clusters set event_type = %s, materiality = %s, updated_at = now() where id = %s", (event_type, materiality, event_id))
    for country in countries:
        country_id = country_ids.get(country.iso2)
        if country_id:
            cursor.execute("""insert into news_event_countries (event_id, country_id, relevance, impact_scope, confidence, transmission_note) values (%s, %s, %s, %s, %s, %s) on conflict (event_id, country_id) do update set relevance = excluded.relevance, impact_scope = excluded.impact_scope, confidence = excluded.confidence, transmission_note = coalesce(excluded.transmission_note, news_event_countries.transmission_note)""", (event_id, country_id, 5 if country.scope == "direct" else 3, country.scope, country.confidence, country.note))
    for slug in indicators:
        if slug in indicator_ids:
            cursor.execute("insert into news_event_indicators (event_id, indicator_id, direction) values (%s, %s, 'ambiguous') on conflict do nothing", (event_id, indicator_ids[slug]))
    for entity in entities:
        entity_id = upsert_entity(cursor, entity, country_ids)
        cursor.execute("insert into news_event_entities (event_id, entity_id, role) values (%s, %s, %s) on conflict do nothing", (event_id, entity_id, entity.role))
    for impact in impacts:
        instrument_id = instrument_ids.get(impact.instrument)
        if instrument_id:
            cursor.execute("""insert into news_event_market_impacts (event_id, instrument_id, impact_scope, expected_direction, confidence, transmission_note) values (%s, %s, %s, %s, %s, %s) on conflict (event_id, instrument_id) do update set impact_scope = excluded.impact_scope, expected_direction = excluded.expected_direction, confidence = excluded.confidence, transmission_note = excluded.transmission_note""", (event_id, instrument_id, impact.scope, impact.direction, impact.confidence, impact.note))
    quality = source_score(article["source_slug"])
    # Source quality validates evidence; it must not turn a routine speech into
    # a market-moving event by itself.
    text = f"{article['headline']} {article.get('summary') or ''}".lower()
    policy_decision = matches(text, ("monetary policy decision", "interest rate decision", "rate decision", "fomc statement"))
    systemic = 5 if event_type == "geopolitics_conflict" else 4 if policy_decision or len(countries) >= 3 else 3
    total = round((materiality * 0.60) + (systemic * 0.30) + (quality * 0.10), 2)
    cursor.execute("""insert into news_event_scores (event_id, source_quality, event_significance, systemic_reach, freshness, total_score, rationale) values (%s, %s, %s, %s, 5, %s, %s) on conflict (event_id) do update set source_quality = excluded.source_quality, event_significance = excluded.event_significance, systemic_reach = excluded.systemic_reach, freshness = excluded.freshness, total_score = excluded.total_score, rationale = excluded.rationale, calculated_at = now()""", (event_id, quality, materiality, systemic, total, "Impact-weighted provisional score: event significance and systemic reach dominate; source quality validates evidence but does not make an event market-moving. Observed reaction is intentionally not yet included."))


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""select distinct on (articles.id) articles.id, articles.headline, articles.summary, articles.published_at, sources.slug, clusters.id::text from news_articles articles join raw_documents raw on raw.id = articles.raw_document_id join sources on sources.id = raw.source_id left join news_event_articles links on links.article_id = articles.id left join news_event_clusters clusters on clusters.id = links.event_id order by articles.id, clusters.created_at asc nulls first""")
            rows = cursor.fetchall()
            cursor.execute("select iso2, id::text from countries"); country_ids = dict(cursor.fetchall())
            cursor.execute("select slug, id::text from indicators"); indicator_ids = dict(cursor.fetchall())
            cursor.execute("select slug, id::text from market_instruments"); instrument_ids = dict(cursor.fetchall())
        created = 0
        with connection.cursor() as cursor:
            for article_id, headline, summary, published_at, source_slug, event_id in rows:
                article = {"headline": headline, "summary": summary, "source_slug": source_slug}
                if event_id is None:
                    _, _, event_type, materiality, _, _ = classify(article)
                    cursor.execute("insert into news_event_clusters (title, event_type, occurred_at, materiality) values (%s, %s, %s, %s) returning id::text", (headline, event_type, published_at, materiality))
                    event_id = cursor.fetchone()[0]
                    cursor.execute("insert into news_event_articles (event_id, article_id) values (%s, %s)", (event_id, article_id))
                    created += 1
                enrich_event(cursor, event_id, article, country_ids, indicator_ids, instrument_ids)
        connection.commit()
    print(f"Created {created} event clusters and enriched {len(rows)} evidence events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
