"""Ingest data/plans.json into the `plans` collection.

One plan or add-on == one vector document, keyed by its catalogue id so
re-running after a price change overwrites in place.

The catalogue is not uniformly shaped: regular plans price with
`monthly_price`, while add-ons use `price` + `price_unit`; `data_gb` is
sometimes a number, sometimes null (meaning unlimited) and sometimes free
text; and only some entries carry `eligibility`, `lines_included` or
`coverage`.  Every field is rendered only when the entry actually has it, so a
document never states a detail the catalogue does not contain.
"""

from __future__ import annotations

import json

from langchain_core.documents import Document

import config
from vectorstore import replace_documents


def _money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _price_lines(plan: dict, currency: str) -> list[str]:
    """Plans price per month; add-ons carry their own unit."""
    lines = []

    if plan.get("monthly_price") is not None:
        lines.append(f"Price: {_money(plan['monthly_price'], currency)} per month")
    elif plan.get("price") is not None:
        unit = plan.get("price_unit", "per month")
        lines.append(f"Price: {_money(plan['price'], currency)} {unit}")

    if plan.get("price_per_line") is not None:
        lines.append(
            f"Effective price per line: {_money(plan['price_per_line'], currency)} per month"
        )
    if plan.get("lines_included") is not None:
        lines.append(f"Lines included: {plan['lines_included']}")

    return lines


def _data_line(plan: dict) -> str | None:
    if plan.get("data_unlimited"):
        return "Data: unlimited"
    data = plan.get("data_gb")
    if data is None:
        return None
    # Add-ons may describe data in words rather than a GB figure.
    if isinstance(data, bool) or not isinstance(data, (int, float)):
        return f"Data: {data}"
    return f"Data: {data} GB"


def _allowance(value) -> str | None:
    """Talk/text allowances are either a word ('unlimited') or a number."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return "not included" if value == 0 else str(value)


def plan_to_document(plan: dict, currency: str, last_updated: str) -> Document:
    """Render one catalogue entry as retrievable text."""
    name = plan.get("name", plan.get("id", "Unnamed plan"))

    lines = [f"Plan: {name} ({plan.get('id', 'unknown')})"]

    descriptor = " | ".join(
        part
        for part in (
            f"Type: {plan['type']}" if plan.get("type") else None,
            f"Category: {plan['category']}" if plan.get("category") else None,
        )
        if part
    )
    if descriptor:
        lines.append(descriptor)

    lines.extend(_price_lines(plan, currency))

    data_line = _data_line(plan)
    if data_line:
        lines.append(data_line)

    talk = _allowance(plan.get("talk_minutes"))
    texts = _allowance(plan.get("texts"))
    if talk:
        lines.append(f"Talk: {talk}")
    if texts:
        lines.append(f"Texts: {texts}")

    if plan.get("hotspot_gb") is not None:
        lines.append(f"Mobile hotspot: {plan['hotspot_gb']} GB")
    for field, label in (
        ("network", "Network"),
        ("coverage", "Coverage"),
        ("contract", "Contract"),
        ("eligibility", "Eligibility"),
        ("intro_offer", "Introductory offer"),
        ("best_for", "Best for"),
    ):
        if plan.get(field):
            lines.append(f"{label}: {plan[field]}")

    features = plan.get("features") or []
    if features:
        lines.append("Features:")
        lines.extend(f"- {feature}" for feature in features)

    lines.append(f"Prices are in {currency}. Plan catalogue last updated {last_updated}.")

    metadata = {
        "source": "plans",
        "identifier": plan.get("id", "unknown"),
        "name": name,
        "category": plan.get("category", "plan"),
        "plan_type": plan.get("type", "plan"),
        "last_updated": last_updated,
    }
    return Document(page_content="\n".join(lines), metadata=metadata)


def load_plan_documents() -> tuple[list[Document], list[str]]:
    catalogue = json.loads(config.PLANS_JSON.read_text(encoding="utf-8"))

    currency = catalogue.get("currency", "USD")
    last_updated = catalogue.get("last_updated", "unknown")

    documents: list[Document] = []
    ids: list[str] = []
    for plan in catalogue.get("plans", []):
        plan_id = plan.get("id")
        if not plan_id:
            continue
        documents.append(plan_to_document(plan, currency, last_updated))
        ids.append(f"plan-{plan_id}")

    return documents, ids


def main() -> None:
    if not config.PLANS_JSON.is_file():
        raise SystemExit(f"Plans catalogue not found: {config.PLANS_JSON}")

    documents, ids = load_plan_documents()
    count = replace_documents(config.PLANS_COLLECTION, documents, ids)
    print(f"Ingested {count} plans into collection '{config.PLANS_COLLECTION}'.")


if __name__ == "__main__":
    main()
