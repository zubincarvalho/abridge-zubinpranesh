"""AuthLens API layer (Agent G).

Thin FastAPI surface over the frozen contracts and ports. Routes validate,
enforce the documented state gates, delegate to the WorkflowOrchestrator
port, and return typed contracts. No clinical logic lives here.
"""
