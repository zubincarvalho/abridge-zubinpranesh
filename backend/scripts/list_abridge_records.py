"""List the official Abridge dataset records and their fixture ids.

Usage (from backend/):
    uv run python scripts/list_abridge_records.py [dataset_path]

Read-only: prints record ids, visit titles, and FHIR resource counts.
"""

import sys

from app.data import load_abridge_dataset


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    dataset = load_abridge_dataset(path)
    print(f"{len(dataset)} records from {dataset.source}\n")
    for record in dataset:
        meta = record.metadata
        counts = meta.get("related_resource_counts", {})
        total = sum(counts.values())
        print(f"abridge:{record.record_id}")
        print(f"    {meta.get('visit_title', '(untitled)')}")
        print(f"    {meta.get('date', '?')[:10]} · {total} FHIR resources · "
              + ", ".join(f"{k}:{v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
