# Dependency requests — Agent A (Data & FHIR)

**None.**

All data and FHIR infrastructure uses the Python standard library
(`json`, `zipfile`, `copy`, `re`, `pathlib`, `threading`) plus dependencies
already declared in `backend/pyproject.toml` (`pydantic`, `pydantic-settings`)
and the existing dev group (`pytest`).

No FHIR client library is requested: the dataset's FHIR R4 resources are
consumed as plain JSON with a purpose-built flattener/indexer
(`backend/app/data/fhir_index.py`), which is sufficient for the demo scope
and keeps original resources byte-identical.
