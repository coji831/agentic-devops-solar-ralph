In the 2026 GitHub Copilot ecosystem, internal memory has evolved from transient chat history into a multi-tiered persistence layer. This system allows AI agents to overcome "contextual amnesia" by building a cumulative knowledge base that grows with every interaction.

### 1. The Two Primary Memory Systems

GitHub Copilot uses two complementary internal memory systems: a remote, automated repository understanding and a local, user-managed notes tool.

| Feature         | GitHub-hosted Copilot Memory (Remote)   | Local Memory Tool (IDE)             |
| :-------------- | :-------------------------------------- | :---------------------------------- |
| **Storage**     | GitHub-hosted (Remote) [1]              | Local machine [1]                   |
| **Creation**    | Automatically by agents during work [1] | By you or the agent during chat [1] |
| **Scope**       | Strictly repository-scoped              | User, repository, or session [1]    |
| **Sharing**     | Shared across IDE, CLI, and Code Review | VS Code only [1]                    |
| **Persistence** | Automatically expires after 28 days     | Manual management [1]               |

### 2. How Copilot "Memorizes" Information

The system uses a process called **Just-In-Time Verification** to ensure it only remembers accurate facts about your project.

- **Deduction:** As you implement tasks or request reviews, Copilot deduces "memories"—tightly scoped pieces of information such as database connection patterns, logging conventions, or synchronization rules between files.[2]
- **Citations:** Every memory is stored with citations—references to specific code locations that support the fact.
- **Verification:** Before applying a stored memory to a new task, the agent validates it against the current codebase. If the code has been refactored and the citation is no longer valid, the memory is discarded or updated to prevent stale data from causing errors.
- **Cross-Agent Learning:** Knowledge discovered by one part of the ecosystem (e.g., a logging convention found by the Code Review agent) is immediately available to other agents (e.g., the Coding Agent implementing a new microservice).

### 3. How to Make Copilot Memorize Your Project

To ensure Copilot effectively retains your project's "tribal knowledge," you should use a combination of automated discovery and explicit instruction files.

#### Enablement and Configuration

- **Individual Users:** Enable **Copilot Memory** in your personal GitHub settings under "Features".[3]
- **Organizations:** Must enable the "Copilot Memory" policy at the organization or enterprise level.[3]
- **IDE Integration:** In VS Code, ensure `github.copilot.chat.copilotMemory.enabled` is set to `true`.[1]

#### Explicit Memory via Instruction Files

To provide a "permanent" memory that never expires, use structured Markdown files in your repository. This is the "Architecture Layer" that governs agent behavior.[4]

- **`.github/copilot-instructions.md`:** Define project-wide styles, naming conventions, and universal "never do this" rules.[5, 4]
- **`AGENTS.md`:** Synchronize all AI agents with team-specific practices. This file acts as a primary source of truth for autonomous worker behavior.[6, 4]
- **`*.instructions.md`:** Use path-specific files (e.g., in `.github/instructions/`) with an `applyTo` glob pattern to provide localized memory for specific frameworks like TypeScript or Python.[6, 7]

#### Interactive Memorization

- **Ask to Remember:** You can explicitly ask an agent to "remember this" during a chat session. The agent will then use its **Memory Tool** to save the note in the local `/memories/repo/` directory.[1]
- **The `/memory` Command:** Use this slash command in modern Copilot versions to quickly open and manage your preferences and instruction file settings.[8]
- **Manage via Settings:** Repository owners can review, curate, and delete stored remote memories by navigating to **Repository Settings > Copilot > Memory** on GitHub.
