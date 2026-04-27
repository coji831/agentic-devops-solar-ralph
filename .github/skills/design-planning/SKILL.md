---
name: design-planning
description: "Use when solution design, architecture-fit analysis, task decomposition, or high-ambiguity tradeoff analysis needs stronger reasoning before coding starts."
argument-hint: "Task or feature to design and decompose"
user-invocable: false
---

# Design Planning

**Dev Stage**: Plan + Design
**Purpose**: Produce a scoped, reviewable design artifact that implementation can follow without ambiguity.
**Loaded by**: `design-planning-architect` when ledger stage = Design

## When to Use

- After scan output is available and a decision on approach is needed
- When a task spans multiple files or modules and dependencies must be mapped
- When there is more than one viable implementation path and tradeoffs need documenting
- When exit criteria in the ledger need to be concretely defined before dispatch

## Procedure

1. Read `verification-artifacts/{task-id}-scan.md` (status: ready).
2. Read relevant existing docs, architecture notes, and instructions files registered in AGENTS.md Repository Context.
3. State the problem in one sentence.
4. List constraints and assumptions explicitly.
5. Identify 1–3 implementation options; select one with brief justification.
6. Define the file-level change plan: which files change, what each change is, order of operations.
7. Define or refine exit_criteria in the ledger — these must be concrete and testable.
8. Write output to `verification-artifacts/{task-id}-design.md`.
9. Append result summary to ledger Decisions Log.

## Output

- `verification-artifacts/{task-id}-design.md` — problem statement, constraints, chosen approach, file-level plan, exit_criteria
- Updated `exit_criteria` row in ledger Loop State
