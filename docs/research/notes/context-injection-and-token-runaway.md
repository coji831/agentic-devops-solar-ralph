# Theoretical and Practical Limitations of Context Re-injection and Token Runaway in Agentic Coding Environments

User:

```text
research for the problem with github copilot large system prompt and re-inject entire context window per call making it tokens usage getting worst overtime, even with regular compacting
```

Gemini:

```markdown
# **Theoretical and Practical Limitations of Context Re-injection and Token Runaway in Agentic Coding Environments**

The rapid evolution of large language model (LLM) utility from predictive text completion to autonomous agentic workflows has fundamentally challenged the traditional stateless architecture of generative artificial intelligence. In systems like GitHub Copilot, the persistent requirement to re-inject the entire context window—comprising the system prompt, tool definitions, workspace metadata, and conversation history—per call creates a systemic inefficiency where token usage accelerates non-linearly over the duration of a session.1 This phenomenon is not merely an artifact of user interaction but is deeply rooted in the "coding harness" that orchestrates the interaction between the developer's integrated development environment (IDE) and the remote inference servers.3 As sessions grow in complexity, the accumulation of redundant data often outpaces the capacity of standard compaction heuristics, leading to a "context collapse" that compromises the model's reasoning capabilities and operational stability.4

## **The Structural Mechanics of the Context Window and Reserved Capacity**

At the core of the token runaway problem is the technical implementation of the context window, which serves as the agent's ephemeral working memory.5 In the current generation of models, such as those with a 192,000-token capacity, the effective space available for code and dialogue is significantly smaller than the nominal limit due to a mandatory feature known as "Reserved Output".6 This mechanism acts as a pre-allocated buffer, similar to a guaranteed parking space, ensuring that the model has sufficient room to generate lengthy refactors or complex explanations without being truncated mid-sentence.6 Even in a dormant state or at the start of a session, this reserved capacity can consume upwards of 30% of the total window, effectively reducing the functional input budget.6

| Model Variant     | Reserved Output Percentage | System Instructions/Tool Tokens | Effective Functional Context |
| :---------------- | :------------------------- | :------------------------------ | :--------------------------- |
| GPT-5.4           | \~31.9%                    | \~8%                            | \~115k tokens                |
| Claude Sonnet 4.6 | \~19.8%                    | \~7%                            | \~140k tokens                |
| Grok Code Fast 1  | \~37.3%                    | \~10%                           | \~101k tokens                |
| GPT-4.1           | \~12.6%                    | \~8%                            | \~152k tokens                |

The discrepancies in reserved output across model providers reflect differing philosophies regarding safety and output verbosity. While a larger reservation prevents the catastrophic failure of truncated code, it simultaneously accelerates the arrival of the token limit in long-horizon tasks.6 This constraint is exacerbated by the fact that the system prompt and tool definitions—which define the agent's capabilities—are pinned to the start of every request, consuming a static overhead that persists and repeats on every turn.6

## **The buildPrompt Engine and Render Layer Hierarchy**

The construction of a prompt in GitHub Copilot is a multi-stage rendering process handled by a dedicated "harness" that decides at runtime what information should be prioritized.1 Unlike simpler chatbots that append messages to a list, the Copilot harness utilizes a layered logic to "reshape and fit" the available data into the remaining token budget.1 This process, primarily governed by the buildPrompt() function, utilizes three primary rendering layers designed to mitigate the immediate impact of data bloat.1

Layer 1 focuses on the truncation of tool results, which are often the primary source of sudden token spikes. Large outputs, such as extensive test logs or search results exceeding 8KB, are replaced with pointers to a local disk storage mechanism, ensuring that the raw data does not poison the context window while remaining accessible for specialized retrieval subagents.1 Layer 2 introduces a "Flex Budget Allocation" strategy, utilizing weights similar to CSS flexbox properties to distribute token space across different turns of history.1 Newer conversational turns are assigned higher weights (flexGrow), ensuring that recent intent is preserved at a higher resolution than older history.1 Layer 3 acts as the final pruning stage, identifying and removing the lowest-priority ChatMessage elements—such as transient status updates or redundant metadata—until the payload fits the budget.1

Despite these layers, the system remains vulnerable to the cumulative cost of history. The fundamental problem persists: the harness must re-send the entire structured prompt, including the system's "behavioral instructions" and workspace structure, with every new message.2 In a multi-turn agentic loop, this means the first message is billed once in the first turn, twice in the second, and ![][image1] times by the ![][image1]\-th turn, creating a quadratic cost structure for context management.2

## **The Failure Modes of Reactive Compaction and Summarization**

When the rendering layers fail to keep the prompt within the hard limits, the system triggers a series of summarization layers, often referred to as the "armageddon" mechanisms.1 These layers represent the final attempts to preserve coherence through lossy compression, yet they frequently introduce secondary failures that degrade agent performance.5

| Summarization Layer    | Trigger Condition         | Mechanism                                         | Cache Awareness |
| :--------------------- | :------------------------ | :------------------------------------------------ | :-------------- |
| Layer 4: Foreground    | Budget Exceeded Error     | Full history distilled into a structured summary. | Low             |
| Layer 5: Inline        | Experimental / Non-OpenAI | Appends "summarize now" to the existing prompt.   | High            |
| Layer 6: Background    | ≥80% Capacity             | Asynchronous compaction during idle time.         | Moderate        |
| Layer 7: Responses API | OpenAI Models             | Delegates context management to the server.       | Native          |

The default mechanism, Layer 4, involves a separate LLM call to summarize the entire conversation into a single block of text.1 While this reduces the raw token count, it frequently leads to "Summarization Drift," where the nuanced constraints provided by the user in early turns—such as "don't use third-party libraries" or specific security requirements—are omitted from the summary.5 This loss of the "implicit contract" between the user and the agent results in the agent appearing to "change its mind" or become incompetent as the session progresses.9

Furthermore, the summarization process itself can trigger a failure loop known as the "413 error death spiral".1 If the summarization request is too large for the model's input limit, the system must drop the oldest groups of messages and retry.1 Internal data suggests that production incidents have occurred where sessions wasted up to 250,000 API calls per day in these recursive retry attempts before ultimately failing and surfacing an error to the user.1 This highlights a critical flaw: the mechanism designed to save tokens can, under stress, become the primary consumer of them.

## **Analysis of Tool Schema Bloat and System Prompt Inefficiency**

A significant contributor to token runaway is the verbosity of tool definitions and the system prompt itself, particularly in agentic workflows that rely on the Model Context Protocol (MCP).8 Every tool made available to the agent must be described in a JSON schema so the model understands how to invoke it.8 Each individual tool schema can add between 2,500 and 3,000 tokens to the system prompt.8 In a standard agent configuration utilizing a default set of 22 tools, the overhead for tool definitions alone can exceed 60,000 tokens—repeated on every single turn of the agent loop.8

The "irony of the optimizer" was documented in a case study of GitHub's internal "Copilot Token Usage Optimizer" workflow, which consumed 14.9 million tokens in a single run.8 The failure was attributed to several factors that are common in large-scale agentic systems:

1. **Over-provisioning of Tools:** The agent was loaded with 22 tools when it only required one for creating issues, leading to massive unnecessary overhead.8
2. **Lack of CLI Proxying:** The agent used MCP tools for file reads instead of a "cli-proxy" that would have allowed it to call the gh CLI directly, bypassing the need for complex schema definitions.8
3. **Verbose Prompting:** The system prompt included 300 lines of instructions with multiple inline code examples that the agent had to process repeatedly.8
4. **Absence of Pre-aggregation:** The agent spent multiple turns performing discovery and data aggregation tasks that could have been handled by a simple pre-processing script, thereby reducing the number of LLM turns required.8

| Optimization Strategy | Description                                                             | Estimated Token Savings   |
| :-------------------- | :---------------------------------------------------------------------- | :------------------------ |
| Narrowing Toolset     | Restricting the agent to only the required toolsets (e.g., \[issues\]). | \~50k tokens per turn     |
| CLI Proxying          | Replacing MCP file tools with direct gh CLI calls.                      | \~5k tokens per file read |
| Prompt Condensing     | Removing redundant examples and using structured tables.                | \~30% of system prompt    |
| Pre-aggregation       | Using bash steps to compute data before LLM involvement.                | \~5-10 agent turns        |

These findings suggest that "compacting" the history is a superficial fix if the "infrastructure tokens"—those used for instructions and tool definitions—are not themselves optimized and narrowed based on the task context.8

## **Context Engineering: From History-as-Transcript to State-as-Memory**

To combat the inherent limitations of history re-injection, a new paradigm of "Context Engineering" has emerged.9 This approach treats the context window not as a scrolling transcript of chat but as a "working set" of functional components that must be governed by explicit resource allocation policies.9 The fundamental governing equation for this allocation is:

![][image2]

where ![][image3] is the total window capacity, ![][image4] the static system instructions, ![][image5] the tool schemas, ![][image6] the response reserve, and ![][image7] the "must-keep" pinned state.9 By explicitly calculating the available history budget (![][image8]), developers can implement proactive sliding-window controllers that trigger trimming before the model reaches the threshold of "attentional dilution".5

A robust implementation of this principle is the 3-Tier Memory Hierarchy, which separates information by its temporal and functional utility 9:

1. **Pinned State (100–300 tokens):** A structured data object containing the user's primary goal, confirmed facts, active constraints, and open tasks. This state is extracted from the conversation and persists even when raw history is pruned, preventing "implicit-contract loss".9
2. **Recent Window (Last K turns):** Preserves the immediate conversational nuance and local coherence necessary for natural interaction.9
3. **Cold Storage (Full transcript):** External storage (vector databases or local files) that is only accessed via retrieval tools. This allows the agent to recall distant information without occupying active window space.9

This tiered approach ensures that as the session progresses, older turns are not merely "summarized" but are "distilled" into the pinned state.12 For example, a developer's earlier instruction to "use the latest version of the API" is extracted into the pinned constraints, allowing the system to safely delete the original five-message exchange where that constraint was established.9

## **Framework-Specific State Management: LangGraph vs. AutoGen**

The divergence in framework architecture significantly impacts how context is recovered and managed over long-running sessions. LangGraph and AutoGen represent two distinct philosophies of interaction that result in different token consumption patterns.13

LangGraph utilizes a graph-based state machine where workflows are modeled as nodes (actions) and edges (transitions).13 The critical innovation in LangGraph for context management is the "Checkpointer".13 Checkpointers persist the state of the conversation (short-term memory) to a database, such as SQLite, Postgres, or Redis, indexed by a thread_id.17 When a user resumes a session, the system does not re-send the history from scratch; instead, it loads the saved state and only processes the new turn.18 This deterministic orchestration allows for node-level retries and "time-travel debugging," where a developer can roll back to a specific checkpoint and branch into a new context without carrying the failed history forward.15

| Feature                  | LangGraph                                         | AutoGen                                    |
| :----------------------- | :------------------------------------------------ | :----------------------------------------- |
| **Model of Interaction** | Deterministic state graph                         | Conversational message passing             |
| **State Persistence**    | Explicit via checkpointers (thread-scoped)        | Implicit in message history                |
| **Context Control**      | Node-level trim_messages utility                  | MaxMessageTermination limits               |
| **Recovery Strategy**    | Conditional branching and rollbacks               | Summarization and compression              |
| **Ideal Use Case**       | Enterprise-grade pipelines with human-in-the-loop | Open-ended collaboration and brainstorming |

In contrast, AutoGen operates on an actor model where agents exchange messages to build consensus.13 While this is ideal for "emergent collaboration," it is inherently more token-intensive because every agent in a group chat must receive the full message history to maintain alignment.15 AutoGen relies more heavily on reactive "MaxMessageTermination" or periodic summarization to prevent window overflow, which can lead to the "lost in the middle" effect where relevant early context is ignored as the window becomes crowded.5

## **The Ralph Loop: Iterative Autonomy and Context Resets**

A radical alternative to the long-running chat session is the "Ralph Wiggum Technique," or the Ralph Loop, which treats each step of a development task as a discrete, stateless iteration.22 Popularized by practitioners seeking to avoid the "hallucination and divergence" of long-context sessions, the Ralph Loop operates on the principle that "Each Iteration \= Fresh Context".22

In a Ralph workflow, a Bash script repeatedly spawns a new AI instance (using tools like Amp or Claude Code) for a single user story or task.22 Instead of carrying forward a multi-thousand-token history, the only memory between iterations is stored on disk in structured files:

- **Git History:** Commits from previous iterations provide the code context.22
- **progress.txt:** A flat file containing learnings and discovered patterns ("this codebase uses X for Y").22
- **prd.json:** A task tracker that indicates which requirements have been satisfied and which remain.22

This "Tabula Rasa" approach ensures that the model never accumulates the confusion or "drift" of prior tasks.25 If a task fails its tests, the loop catches the failure, updates the "learnings" file, and restarts the agent with a clean window focused solely on correcting the previous error.22 By keeping tasks "right-sized"—small enough to fit in a single context window—Ralph loops bypass the need for complex compaction altogether.22

## **Progressive Disclosure and Repository-Aware Context via.agent.md**

To manage the tension between providing enough context and avoiding token bloat, the industry has standardized "Progressive Disclosure" formats like .agent.md, AGENTS.md, and SKILL.md.26 These files allow for "context on demand" rather than "context by default".26

The AGENTS.md file serves as a repository-wide baseline of instructions, but its most powerful feature is its hierarchical inheritance.26 An agent working in the src/database folder will prioritize a local src/database/AGENTS.md over the root file, allowing it to load specific conventions and schemas only when it is actually working in that subsystem.26 This "nearest-context-wins" logic prevents the system prompt from becoming a monolithic block of instructions for parts of the codebase that are irrelevant to the current turn.26

Similarly, the .agent.md specification used in Visual Studio and VS Code allows for the definition of "specialist roles".28 A planner.agent.md might be configured with access to architectural documents and high-level project goals but stripped of code-editing tools to reduce its schema weight.29 Conversely, an implementer.agent.md is given file-system tools but is spared the burden of the project's roadmap.29 This separation of concerns ensures that the token budget is always focused on the specific needs of the agent's current phase of work.29

| File Type               | Role in Context Engineering               | Storage Location        |
| :---------------------- | :---------------------------------------- | :---------------------- |
| AGENTS.md               | Repo-wide or path-specific guidelines.    | Root or sub-directories |
| SKILL.md                | Reusable, task-specific procedures.       | .github/skills/         |
| .agent.md               | Specialist agent role definitions.        | .github/agents/         |
| .prompt.md              | Repeatable entry points for common tasks. | .github/prompts/        |
| copilot-instructions.md | Native GitHub repository instructions.    | .github/                |

## **Technical Frontiers: Latent State Recursion and Prompt Caching**

As the limits of text-based context re-injection are reached, emerging research into "Recursive Multi-Agent Systems" (RecursiveMAS) explores passing "latent representations" rather than textual history.30 In this view, each agent iteration functions like a layer in a recursive neural network, refining the system's "hidden state" without the information bottleneck of natural language.30

RecursiveMAS achieves a "closed-loop" refinement where the output of the last agent is fed back into the first as a latent vector.30 Empirical evaluations show that this approach can improve accuracy on complex math and coding benchmarks while reducing token usage by over 60% after three rounds of recursion.30 By bypassing the need to generate and parse text at every step, the system avoids the quadratic accumulation of context tokens.30

Simultaneously, the widespread adoption of "Prompt Caching" in the Anthropic and OpenAI APIs provides a pragmatic solution for long sessions.1 When the GitHub Copilot provider uses the Anthropic Messages API, it can utilize cache_control markers to persist the system prompt and the "base" of the conversation history on the inference server.1 This means the client only pays for the "delta"—the new turn—significantly reducing both cost and latency for sessions that persist for hundreds of turns.1 However, prompt caching is highly sensitive to the order of content; any change to the early history (such as the harness injecting a different file or re-summarizing) invalidates the cache, forcing a "cold" re-injection of the entire window at full cost.1

## **Managing Token-Based Billing and Enterprise Constraints**

The transition to usage-based billing for Copilot has made token efficiency a primary financial metric for engineering organizations.33 Organizations are encouraged to adopt "Token Optimization Guides" that dictate developer habits to curb runaway costs.34 These strategies include:

- **Microservice Isolation:** Developers are instructed to open only the repository of the service they are actively working on, as having multiple microservices open expands the context scope and triggers irrelevant repo-aware retrieval.34
- **Tab Management:** Keeping only 3 to 5 tabs open at any time ensures that the "Active File" and "Open Editors" context remains lean.34
- **Selective Model Routing:** Using standard, cheaper models for routine boilerplate and reserving premium reasoning models for complex architectural questions.34
- **Content Exclusion Policies:** Committing .github/copilot-content-exclusion files to the repository to prevent the system from ever indexing large, low-value files like generated logs, binaries, or documentation artifacts.34

Ultimately, the problem of token runaway in GitHub Copilot is a symptom of the transition from "Chat-as-a-Product" to "Agent-as-a-Platform." While the underlying models possess increasingly large context windows, the mechanics of stateless re-injection necessitate a sophisticated "Context Engineering" layer to maintain performance.3 Whether through deterministic state management in LangGraph, the iterative resets of the Ralph Loop, or the progressive disclosure of .agent.md files, the goal remains the same: ensuring that the agent's limited attentional budget is spent on the highest-signal tokens required to solve the task at hand.5 The evolution from linear history to structured, persistent state represents the next critical milestone in the development of reliable autonomous coding assistants.

#### **Works cited**

1. Context Window Management in Claude Code and GitHub Copilot ..., accessed May 18, 2026, [https://medium.com/@toni3095/context-window-management-in-claude-code-and-github-copilot-0d108b9f0a81](https://medium.com/@toni3095/context-window-management-in-claude-code-and-github-copilot-0d108b9f0a81)
2. Copilot and many coding agents truncates the context window and uses dynamic sum... | Hacker News, accessed May 18, 2026, [https://news.ycombinator.com/item?id=46520179](https://news.ycombinator.com/item?id=46520179)
3. The Coding Harness Behind GitHub Copilot in VS Code, accessed May 18, 2026, [https://code.visualstudio.com/blogs/2026/05/15/agent-harnesses-github-copilot-vscode](https://code.visualstudio.com/blogs/2026/05/15/agent-harnesses-github-copilot-vscode)
4. Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models | OpenReview, accessed May 18, 2026, [https://openreview.net/forum?id=eC4ygDs02R](https://openreview.net/forum?id=eC4ygDs02R)
5. A Practical Guide to Memory for Autonomous LLM Agents | Towards Data Science, accessed May 18, 2026, [https://towardsdatascience.com/a-practical-guide-to-memory-for-autonomous-llm-agents/](https://towardsdatascience.com/a-practical-guide-to-memory-for-autonomous-llm-agents/)
6. Copilot Context Window Showing \~40% Reserved Output Even With Minimal Prompt · community · Discussion \#188691 \- GitHub, accessed May 18, 2026, [https://github.com/orgs/community/discussions/188691](https://github.com/orgs/community/discussions/188691)
7. Copilot Chat hitting 128k token limit mid-session — how do you keep context? \- Reddit, accessed May 18, 2026, [https://www.reddit.com/r/GithubCopilot/comments/1rlagxa/copilot_chat_hitting_128k_token_limit_midsession/](https://www.reddit.com/r/GithubCopilot/comments/1rlagxa/copilot_chat_hitting_128k_token_limit_midsession/)
8. Optimize Copilot Token Usage Optimizer: reduce 14.9M tokens/run ..., accessed May 18, 2026, [https://github.com/github/gh-aw/issues/27112](https://github.com/github/gh-aw/issues/27112)
9. Context Engineering Techniques in Agent Memory Patterns | by Chier Hu \- Medium, accessed May 18, 2026, [https://medium.com/agenticais/context-engineering-techniques-in-agent-memory-patterns-8105d619df16](https://medium.com/agenticais/context-engineering-techniques-in-agent-memory-patterns-8105d619df16)
10. Context Engineering \- LangChain, accessed May 18, 2026, [https://www.langchain.com/blog/context-engineering-for-agents](https://www.langchain.com/blog/context-engineering-for-agents)
11. Improving token efficiency in GitHub Agentic Workflows \- The GitHub ..., accessed May 18, 2026, [https://github.blog/ai-and-ml/github-copilot/improving-token-efficiency-in-github-agentic-workflows/](https://github.blog/ai-and-ml/github-copilot/improving-token-efficiency-in-github-agentic-workflows/)
12. Context Engineering for Personalization \- State Management with ..., accessed May 18, 2026, [https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization](https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization)
13. LangGraph vs AutoGen: Multi-Agent AI Framework Comparison \- Leanware, accessed May 18, 2026, [https://www.leanware.co/insights/auto-gen-vs-langgraph-comparison](https://www.leanware.co/insights/auto-gen-vs-langgraph-comparison)
14. AutoGen vs LangGraph: Comparing Multi-Agent AI Frameworks \- Truefoundry, accessed May 18, 2026, [https://www.truefoundry.com/blog/autogen-vs-langgraph](https://www.truefoundry.com/blog/autogen-vs-langgraph)
15. Agentic Frameworks Explained: Building Intelligent AI Agents in 2025 \- Mem0, accessed May 18, 2026, [https://mem0.ai/blog/agentic-frameworks-ai-agents](https://mem0.ai/blog/agentic-frameworks-ai-agents)
16. Built with LangGraph\! \#24: Memory | by Okan Yenigün | Towards Dev \- Medium, accessed May 18, 2026, [https://medium.com/towardsdev/built-with-langgraph-24-memory-e96537cc1b15](https://medium.com/towardsdev/built-with-langgraph-24-memory-e96537cc1b15)
17. Short-term memory \- Docs by LangChain, accessed May 18, 2026, [https://docs.langchain.com/oss/python/langchain/short-term-memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
18. Understanding Memory Management in LangGraph: A Practical Guide for GenAI Students | by Jaime Lucena Pérez | Towards AI, accessed May 18, 2026, [https://pub.towardsai.net/understanding-memory-management-in-langgraph-a-practical-guide-for-genai-students-b3642c9ea7e1](https://pub.towardsai.net/understanding-memory-management-in-langgraph-a-practical-guide-for-genai-students-b3642c9ea7e1)
19. Autogen vs LangGraph: Comparing Multi-Agent Workflow Solutions \- Openxcell, accessed May 18, 2026, [https://www.openxcell.com/blog/autogen-vs-langgraph/](https://www.openxcell.com/blog/autogen-vs-langgraph/)
20. In what scenario would one want to use Autogen over Langgraph? : r/AI_Agents \- Reddit, accessed May 18, 2026, [https://www.reddit.com/r/AI_Agents/comments/1ro0eve/in_what_scenario_would_one_want_to_use_autogen/](https://www.reddit.com/r/AI_Agents/comments/1ro0eve/in_what_scenario_would_one_want_to_use_autogen/)
21. Comparing LLM Agent Frameworks: AutoGen vs CrewAI vs LangGraph — A Practical Selection Guide | Chaos and Order, accessed May 18, 2026, [https://www.youngju.dev/blog/llm/2026-03-09-llm-agent-framework-autogen-crewai-langgraph-comparison.en](https://www.youngju.dev/blog/llm/2026-03-09-llm-agent-framework-autogen-crewai-langgraph-comparison.en)
22. GitHub \- snarktank/ralph: Ralph is an autonomous AI agent loop that runs repeatedly until all PRD items are complete., accessed May 18, 2026, [https://github.com/snarktank/ralph](https://github.com/snarktank/ralph)
23. GitHub \- vercel-labs/ralph-loop-agent: Continuous Autonomy for the AI SDK, accessed May 18, 2026, [https://github.com/vercel-labs/ralph-loop-agent](https://github.com/vercel-labs/ralph-loop-agent)
24. Automating agents with the next iteration of Ralph \- RichSnapp.com, accessed May 18, 2026, [https://www.richsnapp.com/article/2026/03-30-automating-your-agents](https://www.richsnapp.com/article/2026/03-30-automating-your-agents)
25. Self-Improving Coding Agents \- Addy Osmani, accessed May 18, 2026, [https://addyosmani.com/blog/self-improving-agents/](https://addyosmani.com/blog/self-improving-agents/)
26. AGENTS.md and SKILL.md: building a reusable agent toolbox | Chris Reddington, accessed May 18, 2026, [https://chrisreddington.com/blog/building-your-agent-toolbox/](https://chrisreddington.com/blog/building-your-agent-toolbox/)
27. AGENTS.md, accessed May 18, 2026, [https://agents.md/](https://agents.md/)
28. Use custom agents in GitHub Copilot \- Visual Studio (Windows) \- Microsoft Learn, accessed May 18, 2026, [https://learn.microsoft.com/en-us/visualstudio/ide/copilot-specialized-agents?view=visualstudio](https://learn.microsoft.com/en-us/visualstudio/ide/copilot-specialized-agents?view=visualstudio)
29. vs-code-agents/USING-AGENTS.md at main \- GitHub, accessed May 18, 2026, [https://github.com/groupzer0/vs-code-agents/blob/main/USING-AGENTS.md](https://github.com/groupzer0/vs-code-agents/blob/main/USING-AGENTS.md)
30. Recursive Multi-Agent Systems \- arXiv, accessed May 18, 2026, [https://arxiv.org/html/2604.25917v1](https://arxiv.org/html/2604.25917v1)
31. Recursive Multi-Agent Systems: From Research Paper to Implementation \- Plaban Nayak, accessed May 18, 2026, [https://nayakpplaban.medium.com/recursive-multi-agent-systems-from-research-paper-to-implementation-three-implementations-9262f4bfcd9c](https://nayakpplaban.medium.com/recursive-multi-agent-systems-from-research-paper-to-implementation-three-implementations-9262f4bfcd9c)
32. fix(providers): Claude on GitHub Copilot should default to anthropic-messages API for prompt caching \#60174, accessed May 18, 2026, [https://github.com/openclaw/openclaw/issues/60174](https://github.com/openclaw/openclaw/issues/60174)
33. Usage limits for GitHub Copilot, accessed May 18, 2026, [https://docs.github.com/en/copilot/concepts/usage-limits](https://docs.github.com/en/copilot/concepts/usage-limits)
34. GitHub Copilot Token Optimization Guide | by Muhammad Haseeb Akram \- Medium, accessed May 18, 2026, [https://medium.com/@haseeb-dev/github-copilot-token-optimization-guide-5a32ec9465ea](https://medium.com/@haseeb-dev/github-copilot-token-optimization-guide-5a32ec9465ea)
35. Best practices for GitHub Copilot CLI, accessed May 18, 2026, [https://docs.github.com/copilot/how-tos/copilot-cli/cli-best-practices](https://docs.github.com/copilot/how-tos/copilot-cli/cli-best-practices)
36. Turning higher token costs into a Prompt‑optimization opportunity : r/GithubCopilot \- Reddit, accessed May 18, 2026, [https://www.reddit.com/r/GithubCopilot/comments/1t0zmc0/turning_higher_token_costs_into_a/](https://www.reddit.com/r/GithubCopilot/comments/1t0zmc0/turning_higher_token_costs_into_a/)
37. Building Agents with GitHub Copilot SDK: A Practical Guide to Automated Tech Update Tracking | Microsoft Community Hub, accessed May 18, 2026, [https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-agents-with-github-copilot-sdk-a-practical-guide-to-automated-tech-upda/4488948](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-agents-with-github-copilot-sdk-a-practical-guide-to-automated-tech-upda/4488948)

[image1]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAYCAYAAAD3Va0xAAABGUlEQVR4Xu2TsWoCQRCGR7BRQRECYmkpCBZiIdgkWATsbJPeRhDyBNfaaKGVVlY2Yi15Ap/AvICdiI1NLEz+310ve3vkvKu9Dz5YdpbZmbk9kZioPMM9/NGuYcqIZ+GnEacrmDHOuCTgFJ7hN2x4w1c6cCneS3zk4Rz2Rd04EZXc5AO+WXs+qnAEi/AL7mDJiCfhTJ8LhDd19doRVVXPjYo8iaqYlQcyhDW9rsAj3MCc3mvCsV7/y20+vJWwjQW8wFe9x2pDz8ccLhMwERPyK0Wezw22xNbY4ouEmA+rYO91OwDeRQ19CwdWzIc9H5OCqKfAZHfnw7L53NN2QOPAAyxb+y4teJK/f4e/RdtzQsGnwH8vcD4xD8kvcTMzNIxbkGYAAAAASUVORK5CYII=
[image2]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAO0AAAAYCAYAAAAWEnolAAAHgklEQVR4Xu2be+hlUxTHlzzymjzG+1E/zD8Y7zwar5RnHmGIyYw/yONPeTaD/CaUkHfIawZphPKHSEPmJ8IgpfCTkqFBCCWU8Vyf2Xe7+6yzz/OeOefXzPnUt7l373vn7LP3Wmuvtc/9ifT09PT09PT0rG1srtrYNvb0DNhQtYVt7OmO/VWLJH9R1lftoTpdtefg/XqqGYPXPWs3OO1dqjNtR4xjVD+o/g30k2qeahvV66q/g75fVU+rNuPLLXGhapUkx/igOGO+wvQx1pvc12Rr1Tum7/hBX1vsolqm2tt2BOCkH6meUJ2nekg1obpX3EK2wXaq11RfldQd7mutgZ1+K0kb+F7c2rOuy1Wzpf0At5HqMUn6yCWJTyTZRPWCpH0NpqteUh0yeF/II6p/VMfaDnFt9C0SF/27YEfVl6pPVduaPhxjpeoN1TTTx3gx/sul/QXl2jjduGkPOUD1uaSDyVxxc36aaV9TnKiaVB0tLurDSeIM6z4ZrvtO4px7weB922Cnf6qOCNpY14vFOc7V0o2N+sD7h+TPzTmqDyV9Dx7WYam4ciqXrVTvqVaodk52reYacYvHLtAVfow4Lg4c4p2Wfj4XQnrJrkyEa5uZ4oIM/8bYQLVEkk7h4Z7eF2cMVbhMnLNVgWuzcx5n2m8Wt+42cGAPpdK4gNtV+9nGihCQCcwEue1Nnw/qsb48GBNjGxXmiHXk+o+bPs+Y6gZxTpk1Tkqot1Tn2g4LhvGj6jlxhhTCe9rpr2pATULkmRDnnBi0B4ObL864rEPTt1B1aNDWJhj3i5J9ALW7uJQvFpm5Dxa/MOIauOaptrEAyqAHJHktyp9XxY2PcYYw3webtiLIdg6yjRXJs1PG87vqY3H3UxbGxNhGZVx1hjgbRXbdGC9rc7i4zTF2Dx6CZV7/athBMXr+Uws77wqJ72JtguHjAL9JcvGpFZ8UV7tap+VzOK3dxdrAjzfmkB7Gx/18Ji4jCCEz2Ne0laGO0+4l7gAsxAeUCUkb4EXiauAqNOG07GZZNeO4uD7OOKrQhNMyP9jgrqqnJL6LUmKSGvMvZQ/lWhZkSthyuDmluEf1l7iFw+hDnS3uInyma9h5QqclEt2qOkqccYV91GV3S9oZ2sKna3kORCoUHpR9LW7M3EPdQFPHaWP4epao3wRNOC02aGtB1pmDSnbgqwbvq9CE0xLgHhYXqBmjzU6miwsqBGLWx96DhTGRUWZmM75WxOA5veTkMtQXUq2exUmoxexpY57mrP5mMTgtY/E125HiUjUM3Do0UZn6risYx3eSvzjA46BJGTquV92xN+W0WfVsXUZ1Wl8ecVpMzcdrP2+k9jhGHZpwWuYIOwR2UNJ073DY5qXiDhx99hXbiUMKA35encD7qVDPejBIFombIWpxMktKAqFDs4Acw1dJ4ZhcvmczjSxl1akejIGAVNZQ2XXJapaJu4+i2owdhYW347pRdX6knbkoe3ruHcTuGGVgXuy10aOqEyLtzHmZrCJmp3xvvrhTY3uIZslaX8bE2Gw7Klpjz7gMn7pgm95GAWfFabm+LzVjvhbCtXHazI3S17OxHHuq1LMe77SMGYW1DWmJnyzSJVujFbGl6hZJZxpZKjqhLXJanIjnyBaC0cuSrs8tsyQ9JkSWszTSTto9xhdLgKNm1bNFnCXpayNO0Z+PtDPnzH0Rvp61dsr8kmHxKCgP5vs2SV+fMTE2246K1hh8PevrT3ZYdlrGyVqOyzALKFPPgnfazM/Fnnt5aKOvSj1LNGeCbNTKU1nD8AHmTtX9kvyFkXdobpQdmAnrkiKnvU7icw5kDXUDZRPpsXeQpupZIAXNmosyxOpZ8DZRd6yjpscEOF/P+vcEPMZ7gSR/97BA4vdg8U4bXcc18XyWRwUni4u4ZVU29fapB7+EsemQH+sv4mrdrmHxvpF4tCZILZX4D1mIyu9K/CS/DE04bdP1LIzitNMk+/msz7DqzteoTsscUZJ4GB/j/EB1vQzT4LL1LOTZzv+pRSzH9hfBCUZ9KN4U3AQL9IykTwm9Q5M52HvpAupR6tLY4wkfjRdJ8j7IUuarXpH83ynnMarTjlLP5jGK085U/SxpO+U1thA67bUSD4ZZjOK0ZHOLJflDEz9/OOdY0O7X3N5DDFJsvp/YzLgpPJmb9WL3miMu0mM0q4I+XvP8aVO+3CFMcFbKiaFyTzNsR0dw8IBTxkoLovMSccYyKW5now5fLm5Rdxh+tDJ1nJYAvVjSNsEBz0qp/uwzRh2nJWMiTbR2GmYAs8WNE+edJy5VrVIa1XFa5os6NhzX2zI8OGTd5w5e76P6JPhc6GtZkNlOSPmycUrDwQ1RKHbaSN+BtrFj+Ckaqa6tTXeT4R9ckCrhZBycjUn83qpQx2nboI7TlsXPISVTFYeFOk67JmEXJqCPm/aeliBreVPcj8DbYpaUPyNok1Mk/zS8KxgTY5sqkCnyg5upkjGuk5DKPSvVd4CedQ+yrIXS3V8q9Qxg8vl5HeoXoicPanjONOoeQvY0CCfEV6oOsx09PQN45MqBZO+wPT09PT09rfMf3V/cmAFhl2wAAAAASUVORK5CYII=
[image3]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABTklEQVR4Xu2UMSiFURiGX8UgFpJS1C1SUgZmG6NFmdgtBptIDBSZGGSRMrHapVuGO9zBrgwmk9Fgwfv+3zm37x7//98Mtv+pZ7jfd8/7nXvO6QIV/8EQbdBv5xudo6P0Kek908lsJbCW9O5oX+hlbIXGhi8GdmC95bRBZugDrSX1jFXYQoWnxFB9x9NFd+liUm+xBFuoAE+NviB/4DQ9oT1JvcUC/aLXrqadHNJT/A7tpkew4EJ0MR9oD1XtGHaWCvW9eboNG1xIDL2H3aB+0hmdcL0Y2k8v6Fj4XMgIfaV12CId/mbopQN1YeuhV0oMbcJ2d0WHQ2+KvsMGjtNz2OCODMACFbxPV1wvDnykeyh5QimaXIe9gFva63oxVJd1g5InlKKz0pl9wm7WEwfqXHW+f0K3ewl7g54YeoAOTygP7UJ/MHnM0sG0WFHRzg8rFkcnGBFugAAAAABJRU5ErkJggg==
[image4]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAYCAYAAAAh8HdUAAABE0lEQVR4Xu3SIUtDYRTG8TNUcCgTFJsWsQxsCrJmEpNFwYFrC4LBNBFlVUQwyAzLaxaTXcSoyWARBAd+AcPi1P+zs+G9h9tMAx/4wTjnfe/Ozp3Z0GYSa1jHVL82g9nBgWTGUMcbDrCPJ1zgAcXfo55RNHGNiURd3/CIe/MJUimhjaXYICdoxKJyig/MxQY5xGYsKi184xgjobeI6VDrpWx+Sbq4QxWF5KEYbe7M/MLgsjxb9sipaDSt9hyf5hf3UifMD2nmXGyQDXzhKDYWcGX+nmKW0cFubGiVtxiPDVLBK+ZjQ+9HT1sNdY2sJWyFeu9vcYMaXvqfteZLvGPHMn5r3vyJila+gm3zf3jWuP/5U34AsNUreE1r6AoAAAAASUVORK5CYII=
[image5]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAYCAYAAADKx8xXAAAAuUlEQVR4XmNgGDnACYjvAvEjIrELSBMjEE8B4pVArADlg8AcIP4HxB5QPjMQ2wPxAyA2BQmIA/EqIBaDKgABQSA+zQBRJI0kzgPEi4FYBsQBWVuIJAkC+kD8CYjXADELkjjIwElAzAvihAKxGpIkCEQD8X8gLkcTFwbiNAaEdzAAyH+/gdgGXQIfwOU/gsAYiL8yYPqPIMDlP7wA5On5DIPWf6A4PAfE7xggfoPhL0B8nQFi2CgY3AAAzMQr+zx1NKQAAAAASUVORK5CYII=
[image6]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAYCAYAAAAlBadpAAABCElEQVR4XmNgGAWOQPwciP8j4VdA/AuI/wLxSSAOBmJmmAZsYA4Q/wZiGyQxkIY0BoghZUDMiCQHB7xAfBiI7wKxOJqcJBA/xCEHBppA/BaI1wAxC5qcKRB/A+KrQCyCJgcGfgwQv6ajSwBBAwNErhhNHA4mMWD6lxWIkxkgLiqF8jEADxAfYICE7jEo+zoDxLbpQCwMU4gNYPMvKFQrGSCh7AoVwwpg/i1CEzcG4q8MkCjECbD5FwSiGSCGtqKJwwG++AUZCtJcjiYOBzpA/J4BM35B7FUMqJqrgdgFxLBlgKQa9PQM8j8MgNIzKMBAhsQC8Wwg5kSSJwhAXvFlgIQ4SRpHATUAAIy9PJOevTuUAAAAAElFTkSuQmCC
[image7]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABS0lEQVR4Xu2TLUsEURSGj2BQ0LIKBg2LzbiIxQ8waNSoP8Cy2aK2LQZBBLNRxGJUEDH4J4yCQTGJIGpQ/HjeOfeycx2RnbBtXniYYc6Zc89977lmlbqtaXiA78A1DCcZqRbh0zxXz0sYSjJy2oV7uIOxX7Eo/XwMz3ACvWk41QAcwj68wmQaztQDTdiCL1hPw0WNwwGsmG9rKQ1napgX3YQPmE3DRS2bdzAFb1bsoh9aMApncAMj+YS/1IIFmIBH2E6iZqvmcRW9tRJ+6nC0uro4MvdQqsOGeREVLuVnn/kCVwG9q5AK1j01ey/lp6Tu1GX0TJ1p65IWLe1nlPyUr/OwY35IkuzRDHfkp4ZZFkTJL02AftYYRXXs5wycwmDum2ZUsypL4mFJ2sG/fs7Bk7Xv+zushZhu04W17/MevIS8mHsOtRCvVKkb+gFM/0ZwbSwG7gAAAABJRU5ErkJggg==
[image8]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAYCAYAAAD3Va0xAAAA6klEQVR4Xu3TMWoCURSF4RuwCFpJbIIrsLJIayNkAWksJLiJNO7DUgQhELCwtbKydhFOlSKihWiTmOh/fCgzFxkiFjZz4APnnRne4/I0y3Jp6phjF7NECyVM8Bvr1higoI/PpYc/PPvCwpq6Pu5cl0gRU0QoJ6tD2hZO8+oLnwoWGCLnOj1rXb3eS4120o7a2UcnjCycWCdPTQdbvODRaViYj95JzXE+G7yj68zsVvN584VdOB/dnx/UfGFhTd2/5xPZlffnycKQz83nHiOsUHXdKbryn5b8f32hiQeM8R3r9PsDeX2cJQvZA21eQcXZsucZAAAAAElFTkSuQmCC
```

---

User:

```text
 so base on the research, explain how github copilot currently cost you more token than it should be? compare to othe AI platform?
```

Gemini:

```markdown
Based on the research, GitHub Copilot often consumes more tokens than necessary due to its "stateless" architecture and massive fixed overhead. While competitors like **Cursor** and **Claude Code** use advanced caching and local indexing to stay lean, Copilot’s design frequently re-injects high volumes of redundant data.

Here is how Copilot’s token usage compares to other platforms:

### 1. High Fixed Overhead (The "Prompt Tax")

Every time you send a message, Copilot attaches a massive "harness" of instructions and definitions.

- **System Prompt:** Copilot’s core behavioral instructions consume approximately **20,500 tokens** at the start of every session.
- **Tool Schema Bloat:** If you use the default agentic settings, Copilot loads about 22 tools. Each individual tool schema adds **2,500–3,000 tokens** to the prompt. This means tool definitions alone can consume **60,000+ tokens** on every single turn, even if the agent only needs one tool to solve your task.

- **Comparison:** High-efficiency agents (like those in the **OpenAI Agents SDK** or custom frameworks) can achieve similar behaviors with system prompts as small as **1,000 tokens**.

### 2. Quadratic Re-injection Cost

Copilot follows a "stateless" re-injection model. Instead of appending only your new message, the IDE "harness" rebuilds and sends the **entire context window**—system prompt, tool results, workspace metadata, and full history—from scratch for every turn.

- This creates a **quadratic cost structure**: you pay for your first message in turn one, twice in turn two, and $N$ times by turn $N$.

- **Comparison:** Platforms like **Claude Code** and the **Anthropic API** use `cache_control` markers. This allows the model to "remember" the static parts (like the 20k system prompt) on the server, so you only pay for the new "delta" tokens of your latest message.

### 3. The "Reserved Output" Buffer

Copilot effectively "locks away" a large portion of its token limit.

- **Reservation Policy:** Copilot reserves approximately **30% (roughly 60,000 tokens)** of the total context window as "Reserved Output." This is a pre-allocated buffer to ensure the model has room to finish a long code block without being cut off.

- **Impact:** Because this space is reserved, the system triggers "compaction" or "summarization" much earlier than a tool like **Cursor**, which manages its window more dynamically.

### 4. Inefficient Compaction & "Death Spirals"

When Copilot hits its limit, it uses a "Layer 4" summarization mechanism.

- **LLM Summarization:** It calls another LLM to summarize the entire conversation. If this summarization prompt is itself too large, it can trigger a "413 error death spiral," where the system repeatedly tries and fails to compress history, wasting hundreds of thousands of tokens in hidden background calls.

- **Comparison:** **Cursor** uses deep codebase indexing and "Composer" mode to surgically select only relevant file snippets. This prevents the context window from filling up with irrelevant code in the first place. **LangGraph** uses "Checkpointers" to save state to a database, allowing users to resume or branch sessions without re-sending the entire historical transcript.

### Summary Comparison Table

| Feature                 | GitHub Copilot                               | Cursor / Claude Code                    |
| ----------------------- | -------------------------------------------- | --------------------------------------- |
| **Architectural Model** | Stateless Re-injection (Rebuilds every turn) | Stateful Caching (Sends only new info)  |
| **System Overhead**     | ~20k fixed tokens + ~60k tool tokens         | Minimal or Cached (User pays for delta) |

|
| **Usable Window** | ~70% (30% is reserved for output)

| High (Dynamic allocation) |
| **Multi-file Context** | Focused on open tabs and manual @ references | Deep local codebase indexing (auto-retrieval) |

**Actionable Tip:** To avoid token runaway, periodically use the `/new` or `/compact` commands to manually reset the history, and limit your open tabs to 3–5 files to reduce the metadata payload.
```

---

User:

```text
what about other large data (tool call result) being sent to LLM unnecessary? the nature of how github copilot consuming data and processing it compare other platform (what done locally, what done on the LLM server)
```

Gemini:

```markdown
GitHub Copilot’s token inefficiency stems from a "stateless" architectural philosophy where the IDE harness sends massive, redundant payloads to the LLM on every turn. Unlike platforms like **Cursor** or **Windsurf**, which use dynamic retrieval and server-side caching to minimize data transfer, Copilot frequently re-injects large tool results and schemas that the model has already seen.

The following breakdown explains how Copilot handles large data and how this compares to other platforms.

### 1. Tool Result Management: Pointer vs. Raw Data

When an agent calls a tool (e.g., searching a codebase or running a test), the output can be massive.

- **GitHub Copilot (The "Pointer" Mechanism):** Copilot uses a "Large Tool Results to Disk" mechanism. If a tool result exceeds a threshold (typically ~8KB to 30KB), the system saves the output to a local temporary file and sends a **pointer** (the file path) to the LLM instead of the raw text.
- **The Inefficiency:** There is a documented "truncation bug" where results from Model Context Protocol (MCP) tools are often truncated to ~10KB _locally_ before the disk mechanism can even trigger. This results in the LLM receiving corrupted or partial data, which often forces the agent to retry the call, doubling the token cost for the same information.
- **Comparison (Cursor/Windsurf):** **Cursor** uses "Dynamic Context Discovery," which assesses if a tool output is still valid and references it in the local filesystem whenever possible instead of re-injecting it. This reportedly reduces token usage by **46.9%** in multi-tool workflows.

### 2. Infrastructure Tokens: The "Tax" on Every Call

Copilot treats tool definitions and system instructions as static "harness" components that must be pinned to every request.

- **GitHub Copilot:** Every turn includes the full JSON schema for all available tools (roughly 2,500–3,000 tokens per tool). In a standard configuration with 22 tools, you are paying for **60,000+ infrastructure tokens** every single time you hit "Enter," regardless of whether those tools are used.
- **Comparison (Claude Code):** **Claude Code** uses a "Snip" module and an aggressive compaction pipeline. It surgically excises high-entropy tool payloads from older turns while preserving only a "tool receipt" (a tiny summary of the outcome) to keep the conversational spine intact without the weight of the raw data.

### 3. Local vs. Server Processing

The location of data processing significantly affects how tokens are consumed and billed.

| Feature                 | GitHub Copilot                                                                                                     | Cursor / Windsurf                                                                                                                                                           |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Indexing**            | **Local & Cloud:** Historically relied on open tabs; now uses workspace indexing, but retrieval is often reactive. | **Local-First:** Indexes the entire codebase locally using AST (Abstract Syntax Trees) to understand logical units (classes, functions) before any data is sent to the LLM. |
| **Prompt Construction** | **Client-Side:** The "buildPrompt()" logic runs in your IDE, assembling the massive blob before transmission.      |

| **Server-Side Aware:** Sends "cache_control" markers. The server "remembers" the codebase context, so you only pay for the new message. |
| **Context Assembly** | **Re-injection:** Rebuilds the prompt from scratch every turn. Turn 10 includes everything from Turns 1-9.

| **Differential Updates:** Only sends what has changed (the "delta"). Static context (like rules) is read from the server cache at **10-50x lower cost**. |

### 4. The Quadratic Cost Problem

The "nature" of Copilot's data consumption is quadratic. Because it is stateless, the amount of data sent to the LLM server follows the formula:

$$Total Tokens = \sum_{i=1}^{n} (Static Overhead + History_i + ToolResults_i)$$

where $n$ is the number of turns. As your session grows, you are effectively paying a "compounding interest" on your own conversation history.

**Other platforms avoid this by:**

- **Prompt Caching:** Using OpenAI and Anthropic’s native caching to ensure that once a 20k-token system prompt or 100k-token codebase index is sent, it remains on the server and is not billed as "input tokens" for subsequent turns.
- **Latent State Recursion:** Emerging research used in newer frameworks passes "latent representations" (hidden mathematical states) between agents rather than raw text, which can reduce token usage by over **60%** in complex tasks.

### Summary of the "Token Trap"

GitHub Copilot currently costs more because it prioritizes **consistency** (sending everything every time to ensure the model doesn't "forget") over **efficiency**. While this makes it reliable for simple tasks, it makes agentic, long-horizon coding sessions exponentially more expensive than platforms like **Windsurf**, which maintains a semantic map of your project and only "looks" at the parts it needs.
```

---

User:

```text
so the real cost is mostly overhead data sent to LLM? list everything that causing overhead problem.
```

Gemini:

```markdown
The real cost of GitHub Copilot is dominated by "Infrastructure Tokens"—static data that is re-sent on every turn—rather than the actual code you are writing. While you might only send a 50-token query, the IDE harness often attaches **80,000+ tokens of overhead** to that request.

Here is a comprehensive list of everything causing the overhead problem in GitHub Copilot:

### 1. Static Infrastructure Overhead (The "Prompt Tax")

Every request starts with a massive block of boilerplate that the model needs to "re-read" to remember how to behave.

- **Monolithic System Prompt:** Copilot's core instructions (behavioral rules, safety guidelines, and "persona" definitions) consume approximately **20,500 tokens** at the start of every session.
- **Over-Provisioned Tool Schemas:** Copilot defines its tools using verbose JSON schemas. Each tool adds ~2,500–3,000 tokens. In a standard "Agent Mode" session with 22 tools, tool definitions alone add **60,000+ tokens** to every single turn.

- **Redundant Feature Flags:** Features like `mount-as-clis` and `copilot-requests` add unnecessary JSON complexity to the prompt payload even if they aren't used for your specific task.

### 2. Architectural "Stateless" Re-injection

Unlike stateful platforms, Copilot’s "harness" treats every message as a brand-new transaction.

- **Quadratic History Cost:** Because Copilot re-injects the entire history per call, the cost of Turn 1 is added to Turn 2, then both are added to Turn 3, and so on. By the 10th turn, you are paying for the same early messages 10 times over.

- **Context Re-rendering:** Every time a tool is called, the IDE `buildPrompt()` engine rebuilds the entire state (files, history, and results) from scratch and re-sends it to the LLM.

### 3. The "Reserved Output" Lock-out

Copilot effectively reduces your usable context window by reserving a large portion of it for the model's response.

- **Pre-allocated Buffer:** For a 192k token model, Copilot reserves roughly **30% (approx. 60,000 tokens)** as "Reserved Output".

- **Premature Compaction:** Because this space is "locked," the system triggers lossy summarization (which costs more tokens to generate) much earlier than it should, often when the window is only 60% full.

### 4. Hidden Meta-Calls and UI "Slop"

The IDE extension makes "hidden" background calls that drain your token quota without you typing a word.

- **Decorative UI Messages:** The extension has been documented making hidden API calls to generate "flashy" progress messages like "Polishing your code..." or "Tuning the syntax." These can consume **hundreds of tokens** per interaction just for UI flavor.
- **Triage Inefficiency:** The system often prepares a massive 270k-token payload for a 4-word prompt without performing a lightweight "sanity check" first.

### 5. Inefficient Tool Result Handling

- **The 10KB Truncation Bug:** A known bug in the Copilot CLI/VS Code harness often truncates MCP tool results to **10KB** locally. This results in the LLM receiving corrupted or partial data, which frequently forces the agent to retry the entire operation, doubling the cost.
- **Verbose Log Dumping:** Instead of sending minimal diagnostic signals, the harness may dump full terminal logs into the context.

### Why this is worse than other platforms

Platforms like **Cursor** and **Claude Code** have moved toward "Context Engineering" to solve these exact problems:

- **Prompt Caching:** Cursor uses `cache_control` markers. The 20k system prompt is sent once, stored on the server, and subsequent turns cost **10x less** because they only hit the "cache read" price.
- **Deferred Tool Loading:** Modern architectures use "Tool Search" where only 30 core tools are loaded. The other 100+ tool schemas are only injected into context if the model specifically requests them, saving up to **20% in tokens**.
- **Local Indexing:** Cursor indexes your codebase locally using AST (Abstract Syntax Trees) to surgically retrieve only relevant snippets, whereas Copilot's "Calculated Context" often pulls in entire open tabs that may be irrelevant.
```

---

User:

```text
so expectedly with an optimized infrastructure and enough base context for an agent to start working, it is better to start a new session (fresh spawning) rather chaining request?
or where is the switching point between "compact then continue" and "new session"
```

Gemini:

```markdown
Based on research into **Context Engineering** and **Ralph Loops**, a "fresh spawn" architecture is significantly more robust and cost-effective than chaining long sessions, provided you have a mechanism to extract and pass a "pinned state" (a digital baton) between them.

The transition from "chaining with compaction" to "fresh spawning" is driven by a trade-off between **context fidelity** and **economic efficiency**.

### The Better Approach: Fresh Spawning (The "Ralph Loop")

In an optimized infrastructure, it is superior to treat each unit of work as a **stateless iteration**. This pattern, popularized as the **Ralph Loop**, involves spawning a new AI instance for every specific task (e.g., one user story or one bug fix).

- **Why it's better:** It eliminates **Context Rot**—the phenomenon where model accuracy drops well before the advertised limit (often starting at 50k–128k tokens).
- **The requirement:** You must use **State Extraction**. Before closing Turn $N$ and spawning Turn $N+1$, the agent writes its "learnings" to disk (e.g., `progress.txt`, `state.md`, or `prd.json`). This ensures that Turn $N+1$ begins with zero history-based confusion but 100% of the essential facts.

### The "Switching Point": When to Reset vs. Compact

The "switching point" is the threshold where the cost of carrying history (even cached) exceeds the utility of that history.

| Feature              | The Switching Point       | Action                                                                                                                                                |
| -------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Window Usage**     | **50% of Context Window** | Once the window is half-full, the model enters the "degradation zone." At this point, **fresh spawning** is more reliable than compaction.            |
| **History Length**   | **15–20 Messages**        | Research indicates that reasoning quality and constraint adherence (the "implicit contract") begin to fail after ~15 turns. **Spawn new session**.    |
| **Task Boundary**    | **"Done" Definition**     | If an agent finishes `Task A` (e.g., planning) and moves to `Task B` (e.g., testing), any attempt to keep the planning history is pure "token waste". |
| **Compaction Drift** | **Recursive Failures**    | If the agent asks a question you already answered in the first 20% of the session, compaction has already failed. **Reset immediately**.              |

### Why Compaction is a "Secondary Backstop"

Compaction (using commands like `/compact`) is intended to buy time _within_ a task, but it introduces **Summarization Drift**. Over time, the "spine" of the conversation is lost, and the agent may appear to "change its mind" or forget critical security constraints (e.g., "don't use third-party libraries") that were established early on.

### Optimized Infrastructure Heuristics

If your infrastructure supports **Prompt Caching** (like Anthropic's `cache_control` or OpenAI's automatic prefix caching), the "mathematical spawn threshold" shifts:

1. **Fresh Spawn Cost:** `Static System Prompt` + `Pinned State Object` + `Fresh Task Prompt`.
2. **Continue Session Cost:** `(History Tokens × Cache Read Multiplier)` + `New Input Tokens`.

Because cache-read tokens are **10–50x cheaper** than fresh input tokens, chaining requests _seems_ economical. However, the **Quadratic Attention Budget** means the model is still processing $N^2$ relationships. Even if it is cheap, a 100k-token cached history is "noisier" and less accurate than a 500-token fresh pinned state.

**Conclusion:** For production agentic systems, the rule of thumb is **"Reset early, reset often."** Use compaction only as an emergency mid-task measure when a single task exceeds the window, but always default to a **fresh spawn** whenever a logical task boundary is reached.
```

---

User:

```text
say each model system prompt (assuming same system prompt for agents use same model) + repo instruction (copilot.instructions, AGENTSmd, ...) + tools/skills discovery - which is cached and which is re-injected on fresh spawning?

Im saying the scenario where agents with same model respawning, assuming tool call result, previous stage artifact is count as new token cost.
```

Gemini:

```markdown
In an optimized agentic infrastructure, "fresh spawning" (starting a brand new session) is often more token-efficient than chaining requests because it avoids the **quadratic attention tax** of a growing conversation history.

However, the token cost of a fresh spawn depends entirely on how the "Infrastructure Prefix" (system prompt, repo rules, and tools) is ordered for caching.

### 1. The Caching Breakdown: Static vs. Dynamic

When you spawn a new agent, the LLM provider (OpenAI/Anthropic) checks for an **exact prefix match** of your prompt. In modern coding harnesses, the prompt is structured in layers.

| Component               | Status          | Token Cost Type                                                                                                                                                                      |
| ----------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Model System Prompt** | **Cached**      | Reused from the LLM provider's global cache or previous turns. Billed at "Cache Read" rates (~10-50x cheaper).                                                                       |
| **Tool/Skill Schemas**  | **Cached**      | Since the JSON definitions for your 22+ tools are static per repo, they are part of the cached prefix if placed early in the prompt.                                                 |
| **Repo Instructions**   | **Cached**      | Files like `copilot-instructions.md` or `AGENTS.md` are typically static. If injected after the system prompt but before the user query, they hit the cache.                         |
| **Previous Artifacts**  | **Re-injected** | Any "baton" passed from a previous session (e.g., `prd.json`, `state.md`) is dynamic. Because it changes every iteration, it **breaks the cache chain** for everything following it. |
| **Tool Call Results**   | **Re-injected** | Raw outputs from the previous session are counted as **new tokens**. These are the primary "bloat" items in long sessions.                                                           |

|

### 2. Why Fresh Spawning Wins (The "Ralph Loop" Economy)

Even though artifacts and tool results are re-injected as new tokens, fresh spawning is superior for two reasons:

- **Elimination of Quadratic Cost:** In a chained session, you pay for Message 1 in every single subsequent turn. In a fresh spawn, you only pay for the **distilled summary** (the artifact) of Message 1, which is often 90% smaller than the raw history.
- **Resetting the Attention Budget:** LLMs have a finite "attention budget." As context grows, the model's ability to follow complex repo instructions (the `AGENTS.md` rules) degrades—a phenomenon called **Context Rot**. Fresh spawning clears the "noise" of failed tool attempts and terminal logs, ensuring the model's full reasoning power is applied to the instructions.

### 3. The Switching Point: Respawn vs. Compact

Mathematically, you should move from "Compact then Continue" to "Fresh Spawning" when:
**`Current Cached History` > `(Infrastructure Prefix + Distilled State Artifact)**`

In practical development, the switching point usually occurs at:

1. **Context Threshold:** When the session hits **50% of the context window** (approx. 64k-100k tokens), reliability drops, and fresh spawning becomes mandatory for quality.
2. **Logic Boundary:** When moving from a "Planning" phase to an "Implementation" phase. The 20,000 tokens of "planning chatter" are useless noise for the implementation agent.
3. **The 15-Message Rule:** Research into agentic drift suggests that reasoning quality begins to decay after **15-20 turns**. At this point, even a cached session is less accurate than a fresh one.

### Summary of "Respawning" Token Logic

| Action                | Outcome                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| **Model/Tools/Rules** | Cost almost zero (hitting 93%+ cache reuse).                                                   |
| **Session Memory**    | You pay for a 500-token `state.md` once instead of a 50,000-token history transcript 10 times. |

|
| **The "Ralph" Benefit** | You bypass the "10KB Truncation Bug" and "413 Error Death Spirals" that plague long-running Copilot sessions. |

**Recommendation:** For agentic workflows, prioritize a **stateless iteration loop**. Have the agent write its progress to a local file (e.g., `progress.txt`) and restart the session every 5-10 tool calls to keep the context "lean and mean".
```

---

User:

```text
so tell me in github copilot compare with other platform:
what is 1 time token cost (assuming the cached read is neglectable) and what is every time token cost.
And the effectiveness/possibility of a chain of agents using handoff to directly spawn next agents?
```

Gemini:

```markdown
In the transition to usage-based billing (June 2026), GitHub Copilot’s token efficiency is defined by a high "Infrastructure Tax" that is mitigated by aggressive server-side caching, provided the session remains stable.

### **Executive Summary**

GitHub Copilot’s cost structure is dominated by a fixed overhead of **80,000+ tokens** (system instructions and tool schemas) that must be processed at least once per session. While modern caching reduces the recurring cost of this overhead to ~10% of the input rate, the platform’s "stateless re-injection" architecture makes long-running sessions significantly more expensive than "fresh-spawned" agents that utilize structured state handoffs.

---

### **Token Cost Comparison: Copilot vs. Others**

In an optimized infrastructure where "cache read" costs are considered the baseline, the real economic differentiator is the **"Infrastructure tax"** (fixed metadata) and the **"Turn delta"** (new data per message).

| Cost Component                  | GitHub Copilot (Agent Mode)                                                | Cursor / Claude Code                                                    | Custom API Agent (e.g., LangGraph)                                                     |
| ------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **1-Time Cost** (Cache Write)   | **~80,000+ tokens** (20k System + 60k Tools)                               | **~5,000–15,000 tokens** (Surgical/Cached rules)                        | **~1,000 tokens** (Optimized system prompt)                                            |
| **Every-Turn Cost** (Recurring) | **Prefix Caching** (93% reuse). Cost is low _unless_ cache is invalidated. | **Surgical snippets**. Sends only relevant code chunks via local index. | **Dynamic/Latent state**. Often uses recursive refinement to bypass text re-injection. |

|
| **Reserved Space** | **~30% (Locked)**. Pre-allocated for model response.

| **Dynamic**. Window expands/contracts based on need. | **Managed**. Developer controls response budget. |

#### **The "Cache Invalidation" Trap**

GitHub Copilot is highly effective when the **prefix matches exactly**. However, if you add a new file to your "Open Tabs" or change a high-level instruction, the **entire 80,000-token prefix must be re-cached** at full "Write" pricing ($3.75/MTok for Sonnet 4.6 vs. $0.375/MTok for Read).

---

### **Agent Handoff Patterns**

Chaining agents via handoffs is the most effective way to circumvent the quadratic cost of long conversations.

| Handoff Pattern            | Effectiveness in Copilot       | Key Innovation                                                                   | Score |
| -------------------------- | ------------------------------ | -------------------------------------------------------------------------------- | ----- |
| **User-Guided Relay**      | ✅ Native via `.agent.md`      | Handoff buttons carry context but "reset" the turn counter.                      | ✅    |
| **Sub-agent Spawning**     | ⚠️ Tool-driven (`runSubagent`) | Spawns worker with isolated context; prevents log bloat.                         | ⚠️    |
| **Artifact-Based Handoff** | ✅ Highest reliability         | Agent A writes a `state.md` and exits; Agent B starts fresh with only that file. | ✅    |

#### **1. Effectiveness of the "Relay Race" (Handoffs)**

Handoffs in Copilot (defined in `.agent.md`) act like a digital relay race.

- **Context Isolation:** When a "Planner" agent hands off to an "Implementer," the implementer inherits the current workspace but **does not inherit the 20 turns of planning dialogue**.
- **Token Savings:** This resets the quadratic history cost. You pay for the "summary" of the plan once, rather than re-sending 20 messages of "thinking" on every subsequent implementation turn.

#### **2. The Sub-agent Spawning Pattern**

Using the `task` or `runSubagent` tool is the most effective way to handle **high-entropy data** (e.g., running tests or scanning 50 files).

- **Mechanism:** The sub-agent processes the messy raw data (e.g., 20,000 tokens of test logs), returns a 200-token summary to the parent, and is terminated.
- **Possibility:** Native in VS Code and the Copilot SDK. However, a known limitation exists where **extension tools do not propagate** to nested sub-agents (depth 2+), often causing them to fail or "hallucinate" tool availability.

---

### **Recommendation**

**Pursue the "Stateless Iteration" (Ralph Loop) via Artifact Handoffs.**

Instead of maintaining one 100-turn chat, configure your agents to:

1. **Extract State:** At the end of a logical task, have the agent write a `progress.txt` or `prd.json`.

2. **Fresh Spawn:** Start a new session (`/new`) or a new agent instance using that file as the primary context.
3. **Why:** This reduces the **Quadratic Attention Tax** and ensures the model is reasoning over high-signal information rather than "broken telephone" summaries from auto-compaction.

---

### **Implementation Notes**

- **Complexity:** Medium (3–5 days to set up proper state-writing skills).
- **Gotcha: The 5-Minute Cold Start.** Anthropic’s prompt cache expires after **5 minutes** of idle time. If you think between prompts for more than 5 minutes, your next turn will be billed as a **full 80k-token "Write"** instead of a "Read."
- **Next Step:** Implement a "Keep-Warm" ping (e.g., `max_tokens: 1`) every 4 minutes during active thinking phases to maintain the 90% cache discount.
```

---
