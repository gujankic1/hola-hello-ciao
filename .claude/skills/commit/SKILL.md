---
name: commit
description: Write and create a git commit (or amend one) in this repo's commit message style. Use whenever the user asks to commit, amend, or reword a commit message.
---

Only commit when the user asked for it. Never push.

## Before committing

1. Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`. Don't commit on failures; report them.
2. Stage only the files that belong to this change, by path (no `git add -A`). Leave unrelated files (e.g. `.claude/`, stray `.db` files) out and say so.

## Message format

```
<Imperative subject, <= 72 chars, no trailing period>

* <what is new or changed>
* <what is new or changed>
```

- Subject: imperative mood ("Add", "Fix", "Refactor"), says the outcome.
- Body: a few `* ` bullets, one per line, short. Brief beats complete.
- Describe only the **net change against what's already pushed** (`@{u}..HEAD`): new behaviour, new endpoints, new decisions (ADRs), or refactors of code that existed before.
- Leave out:
  - Iterations made while building the same commit (e.g. "added a repository layer" to code that is itself new in this commit, "split the tests").
  - Things that go without saying: tests added, docs/README kept in sync, formatting, lint fixes.
  - Restating the subject.
- No `Co-Authored-By` or any other attribution line.
- Explain *why* in a bullet only when it isn't obvious from the change.

## Amending

When amending, rewrite the message from scratch against `@{u}..HEAD` so it describes the commit as a whole, not the history of how it got there.

After committing, show `git log -1 --format='%h%n%B'`.
