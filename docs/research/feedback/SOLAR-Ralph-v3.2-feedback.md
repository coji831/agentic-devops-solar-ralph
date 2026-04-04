realign the research plan with these feedbacks:

- orchestrator overdo it task ( load skill when no needed, do no delegation and jump to execute), orchestrator must be super light weight and only need to be accuracy when distribute task

- pipeline are being too adapted to a target project (narrow use case), it need to be more generic with out the need of caring about context from the workflow

- work flow extraction need improvement (coverage and detail), better for create/update new flow, (extract all and request user to verify is okay)

- some high reason agent (design) are doing too much (generate full code on planning, write docs), leaking token

- pipeline start/run time longer than expected (too much reasoning, need some performance setting or optimized prompting)

- AGENTs.md need to be more simple and generic

- More quantity and quality of discussion of between agents use the share context (but still optimize for token usage)

- the implementer must ask for guide/template/sample code, if unclear, do not make assumption or code before design/plan is ready

- the planer/designer must not provide full code, only high level structurer, template, instruction then pass to the implementor

- pipeline must have skip mechanic for steps if the target project not required (to extract the pipeline definition from it indexing, reduce memory inject, and allow update injection)

- more direct instruction for simple task rather than let the agent polluting it context by reasoning

- agents/prompt writing must cover larger spectrum rather than deep dive to specific use case, the fine tuning must be delegate for custom workflows/instructions

- lack of human in the loop mechanic (no self reflect and update when user intervien)

- lack of self improve (no record mistake - instruction/work flow, etc - when rejected by reviewer, only write to the ledger which only live in the current itteration)

- implementor/doc writer some time output without keeping format or wrong position (stricter when give instruction/design/plan)

- per agent instruction/workflow , to be unpdate/inject when a sefllearning happen (under custom workflow folder for solar system only, not interfere with target project existing system or main instruction)

- logs for report/improvement (vs code extension, mcp, text file, etc.)
