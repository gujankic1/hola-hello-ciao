# Architecture documentation (arc42, lean)

We use [arc42](https://arc42.org/) in a deliberately minimal form: only chapters that have real content exist. Add a chapter when there is something worth recording; don't create empty ones.

| # | Chapter | Status |
|---|---|---|
| 1 | [Introduction and goals](01-introduction-and-goals.md) | started |
| 2 | [Constraints](02-constraints.md) | started |
| 3 | [Context and scope](03-context-and-scope.md) | started |
| 4 | [Solution strategy](04-solution-strategy.md) | started |
| 5 | [Building blocks](05-building-blocks.md) | started |
| 6 | Runtime view | not yet written |
| 7 | [Deployment](07-deployment.md) | started |
| 8 | [Cross-cutting concepts](08-cross-cutting-concepts.md) | started |
| 9 | [Architecture decisions](09-architecture-decisions.md) | ADR-001 to ADR-006 |
| 10 | Quality requirements | not yet written (quality goals: chapter 1) |
| 11 | [Risks and technical debt](11-risks-and-technical-debt.md) | started |
| 12 | Glossary | not yet written |

## Rules

- Update the affected chapter in the same change as the code.
- Significant decisions become an ADR in chapter 9 (append-only; supersede, don't rewrite).
- Keep it short. Link to code instead of duplicating it.
