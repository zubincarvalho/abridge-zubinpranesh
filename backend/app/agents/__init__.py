"""AuthLens agent wiring surfaces.

Namespace package for the per-stage port-facing entry points (policy parser,
evidence retriever/mapper, gap detector, disclosure, packet generator,
verification). Created by the integration agent per
docs/PARALLEL_EXECUTION.md. Each module is a thin factory over an
implementation in ``app.services`` and depends only on frozen contracts and
ports.
"""
