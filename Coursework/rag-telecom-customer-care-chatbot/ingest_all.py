"""Run every ingest script in sequence -- the one-command knowledge build."""

from __future__ import annotations

import ingest_faq
import ingest_guide
import ingest_plans
import ingest_tickets


def main() -> None:
    ingest_faq.main()
    ingest_tickets.main()
    ingest_guide.main()
    ingest_plans.main()
    print("\nKnowledge base ready. Start the UI with: streamlit run app.py")


if __name__ == "__main__":
    main()
