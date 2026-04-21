# Learning Format Converters

Converter templates for promoting entries from the learning system (PATTERNS.md, ERRORS.md) into permanent governance artifacts (instructions, workflows, skills, knowledge base).

## Overview

The learning system captures raw signals during task execution. Converters transform those raw signals into the correct format for their destination. The Orchestration Governor generates a **Learning Promotion Report** at pipeline CLOSE; these converter templates are the formats the governor uses when producing output for user approval.

## Converter Index

| Converter | Input | Output Destination |
|-----------|-------|-------------------|
| [patterns-to-instructions](patterns-to-instructions.md) | PATTERNS.md entry | `.github/instructions/*.instructions.md` |
| [patterns-to-workflow](patterns-to-workflow.md) | PATTERNS.md entry | `.github/workflows/*.workflow.md` |
| [patterns-to-skill](patterns-to-skill.md) | PATTERNS.md entry | `.github/skills/*/SKILL.md` |
| [errors-to-instructions](errors-to-instructions.md) | ERRORS.md entry | `.github/instructions/*.instructions.md` (troubleshooting section) |

## Workflow

```
Task completes
    ↓
Orchestrator scans PATTERNS.md + ERRORS.md at pipeline CLOSE
    ↓
Classifies entries: HIGH / MEDIUM / LOW
    ↓
Generates Learning Promotion Report (table of entry + classification + suggested destination)
    ↓
User approves report
    ↓
Orchestrator uses appropriate converter template to format content
    ↓
Docs Curator writes converted content to destination file
    ↓
Promoted entries marked with <!-- promoted: [DATE] --> in source file
    ↓
(Optional) solar-cleanup-learning.prompt.md removes promoted entries after 30-day grace period
```

## Duplicate Detection

Before inserting converted content into any destination file, the Docs Curator MUST:

1. Read the full target file
2. Search for entries with similar key phrases (any 2 of the 3 main keywords from the entry title)
3. If a similar entry exists: flag as `DUPLICATE_CANDIDATE: <existing entry>` to `## Handoff Payload` and surface to user for review
4. Never auto-insert when a duplicate candidate exists
5. Add cross-reference comment on insert: `<!-- Source: PATTERNS.md #[ENTRY-DATE-TITLE] -->`

## Classification Guide

| Classification | Criteria | Typical Destination |
|---------------|----------|-------------------|
| HIGH | Affects all agents or all pipelines; applies to any project | `conventions.instructions.md` or `workflow.instructions.md` |
| MEDIUM | Domain-specific; applies to frontend, backend, or docs work | `frontend.instructions.md`, `backend.instructions.md`, or a skill SKILL.md |
| LOW | Task-specific; applies only to the current project's stack | `architecture.instructions.md` or project-local notes |
