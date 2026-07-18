"""Policy parser port.

Parses a payer medical-necessity policy document into discrete criteria
(prompt-chaining stage 1). Criteria must quote or faithfully restate the
policy text — the parser must not invent requirements.
"""

from typing import Protocol

from app.contracts import PayerPolicy, PolicyCriterion


class PolicyParser(Protocol):
    def parse(self, policy: PayerPolicy, policy_text: str) -> list[PolicyCriterion]:
        """Return the discrete criteria found in ``policy_text``.

        Each criterion gets a stable ``criterion_id`` and a routing
        ``category`` used to select the retrieval strategy.
        """
        ...
