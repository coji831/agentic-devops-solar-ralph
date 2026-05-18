# Verification Artifacts

Task-scoped artifact storage for the SOLAR-Ralph agent harness.

## Lifecycle Rules

- **Create**: Governor creates `{task-id}-input.json` when task is assigned to ledger
- **Fill**: Specialist writes content when material status = ready
- **Clean up**: Governor deletes `{task-id}-*` files at TASK_COMPLETE

## Naming Convention

`{task-id}-{type}.json`

Types: `input`, `scan`, `design`, `impl`, `test`, `verify`, `docs`, `ledger-archive`

## Default State

Empty. Only populated during active tasks.