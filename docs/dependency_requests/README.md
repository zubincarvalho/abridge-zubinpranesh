# Dependency requests

One file per agent (names in PARALLEL_EXECUTION.md). Never edit
`backend/pyproject.toml` directly and never write in another agent's file.
Format and review bar: docs/DEPENDENCY_POLICY.md. The integration agent
applies approved requests in a single pass.
