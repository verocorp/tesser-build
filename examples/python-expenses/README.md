# Python acceptance-gate output — "Expensewell"

This is the **fresh-agent acceptance-gate output** for the verified Python
rendering (skill-version 4), the Python peer of the Go gates that produced
`examples/lending` (v2) and `examples/running` (v3).

A fresh agent with **no design knowledge** was given only
`skills/ddd/SKILL.md` (and the files it routes to) plus a neutral
expense-report task — the temptations embedded but **never named** (no mention
of value object, entity, aggregate, application service, repository, public
interface, composition root, or DTO). It produced this expense-report service
from the skill alone. It was then independently verified and audited (see
`docs/sessions/2026-07-12-skill-v4-python-gate.md`): `mypy --strict` and
`pytest` clean, and every structural property held — the aggregate enforces its
invariants in the constructor and re-establishes them on each transition, the
total is computed on the aggregate (not the service), responses are DTOs (no
domain-object leak), the public `Client` `Protocol` is satisfied structurally,
and only the composition root imports the concrete implementation.

Committed as-produced (only self-inflicted mypy nits were fixed by the agent),
so it stands as an honest record of what the skill is sufficient to build. Run
it the same way as `examples/python` (see that directory's README).
