---
name: implementation
description: "Use when implementing code changes in a repository where domain-specific specialists are not installed. Generic — no stack assumptions. Stack context loaded from the project's .instructions.md at runtime."
argument-hint: "Design artifact path and task-id to implement"
user-invocable: false
---

# Implementation

**Dev Stage**: Implement
**Purpose**: Execute the file-level change plan from the design artifact without expanding scope.
**Loaded by**: `implementation-specialist` when ledger stage = Implement

## When to Use

- After a design artifact has been produced and approved (G2 gate passed)
- When all input materials are ready and exit_criteria are defined in the ledger
- For any code, config, or non-documentation file change

## Procedure

1. Read `verification-artifacts/{task-id}-design.md` (status: ready).
2. Load any path-specific `.instructions.md` files that cover the files being changed.
3. Execute the file-level change plan from the design artifact in the stated order of operations.
4. Do not add features, refactor code, or make improvements beyond what the design specifies.
5. After all changes: verify the output compiles / passes static analysis if a check command is available.
6. Write output summary to `verification-artifacts/{task-id}-impl.md` (list of files changed + brief description of each change).
7. Append result summary to ledger Decisions Log.

## Output

- Code/config/doc changes as specified in the design artifact
- `verification-artifacts/{task-id}-impl.md` — list of files changed and what changed in each
