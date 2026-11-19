# Architecture documentation (arc42, lean)

We use [arc42](https://arc42.org/) in a deliberately minimal form: only chapters that have real content exist. Add a chapter when there is something worth recording; don't create empty ones.

- [1. Introduction and goals](01-introduction-and-goals.md)
- [2. Constraints](02-constraints.md)
- [3. Context and scope](03-context-and-scope.md)
- [4. Solution strategy](04-solution-strategy.md)
- [5. Building blocks](05-building-blocks.md)
- [7. Deployment](07-deployment.md)
- [8. Cross-cutting concepts](08-cross-cutting-concepts.md)
- [9. Architecture decisions](09-architecture-decisions.md)
- [11. Risks and technical debt](11-risks-and-technical-debt.md)

## Rules

- Update the affected chapter in the same change as the code.
- Significant decisions become an ADR in chapter 9; when the reasoning changes, update the ADR in place.
- Keep it short. Link to code instead of duplicating it.
