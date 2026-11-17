# Architecture documentation (arc42, lean)

We use [arc42](https://arc42.org/) in a deliberately minimal form: only chapters that have real content exist. Add a chapter when there is something worth recording; don't create empty ones.

| # | Chapter | Status |
|---|---|---|
| 1 | [Introduction and goals](01-introduction-and-goals.md) | started |
| 2 | [Constraints](02-constraints.md) | started |
| 3 | Context and scope | not yet written |
| 4 | [Solution strategy](04-solution-strategy.md) | started |
| 5 | [Building blocks](05-building-blocks.md) | started |
| 6 | Runtime view | not yet written |
| 7 | [Deployment](07-deployment.md) | started |
| 8 | Cross-cutting concepts | not yet written |
| 9 | [Architecture decisions](09-architecture-decisions.md) | ADR-001, ADR-002 |
| 10–12 | Quality, risks, glossary | not yet written |

## Rules

- Update the affected chapter in the same change as the code.
- Significant decisions become an ADR in chapter 9 (append-only; supersede, don't rewrite).
- Keep it short. Link to code instead of duplicating it.
