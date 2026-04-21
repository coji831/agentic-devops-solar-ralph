# Pipeline to Workflow Migration Map

Status: active
Schema Version: 1.0

## Mapping Table

| Legacy pipeline file                                      | New workflow file                          | Type       | Fallback when workflow mode is disabled |
| --------------------------------------------------------- | ------------------------------------------ | ---------- | --------------------------------------- |
| `.github/solar-system/pipelines/pipeline-1-knowledge.md`  | `.github/workflows/knowledge.workflow.md`  | knowledge  | Use legacy pipeline file directly       |
| `.github/solar-system/pipelines/pipeline-2-simple-fix.md` | `.github/workflows/simple-fix.workflow.md` | simple-fix | Use legacy pipeline file directly       |
| `.github/solar-system/pipelines/pipeline-3-bug-fix.md`    | `.github/workflows/bug-fix.workflow.md`    | bug-fix    | Use legacy pipeline file directly       |
| `.github/solar-system/pipelines/pipeline-4-feature.md`    | `.github/workflows/feature.workflow.md`    | feature    | Use legacy pipeline file directly       |

## Mode Selection Rules

1. If `.github/solar.config.json` has `workflow_mode: "workflow"`, prefer `.github/workflows/*.workflow.md`.
2. If workflow metadata does not match schema, emit a warning and continue using the workflow file.
3. If `workflow_mode: "pipeline"`, always use `.github/solar-system/pipelines/*.md`.

## Verification Targets

- Every workflow file includes minimal frontmatter: `name`, `type`, `loop`, `max_iterations`, `exit_condition`.
- Governor selection logic can resolve all 4 core workflow types.
- Fallback path is deterministic for each workflow.
