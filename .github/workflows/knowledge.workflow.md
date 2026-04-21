---
name: knowledge
type: knowledge
loop: false
max_iterations: 1
exit_condition: "Question answered with traceable evidence and no implementation changes."
---

# Pipeline 1: Knowledge

**Signal:** question, explanation, "what is", "how does", code lookup

## Pipeline Stages

```
Governor → Answer directly. No ledger task. No loop. No specialists.
```

Session-Type: `chat`. No delegation required for pure knowledge queries.
