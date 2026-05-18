---
agent: agent
description: Sync the SOLAR-Ralph registry in AGENTS.md after adding, swapping, or removing any component
---
You are updating the SOLAR-Ralph component registry.

Use the vscode_askQuestions tool to ask:
1. What changed? (added / swapped / removed)
2. Which component type? (agent / skill / instruction / hook / workflow)
3. What is the file path of the new or updated file?

Then:
- ADD agent: read the file → add a row to Agent Registry with Dev Stage + Loads Skill columns filled
- ADD skill: read the file → add a row to Skill Index with Dev Stage column filled
- ADD playbook: read the file → add a row to Playbook Index with Name, Description, Path, Trigger filled
- SWAP: read new file → update the existing row (Name, Dev Stage, Loads Skill, Accepts, Produces)
- REMOVE: confirm file deleted → remove the row
- Optional component: add row with Optional=Yes + enable instruction

Print a summary of all AGENTS.md changes made.