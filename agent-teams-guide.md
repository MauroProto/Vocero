# Claude Code Agent Teams Guide

## What Are Agent Teams?

Agent teams coordinate **multiple independent Claude Code sessions** working together. One session acts as the **team lead** (orchestrator), spawning **teammates** — each a full, separate Claude Code instance with its own context window and tools.

### Agent Teams vs Subagents

| | Subagents | Agent Teams |
|---|---|---|
| **Context** | Own context window; results return to caller | Own context window; fully independent |
| **Communication** | Report results back to main agent only | Teammates message **each other** directly |
| **Coordination** | Main agent manages all work | Shared task list with self-coordination |
| **Best for** | Focused tasks where only the result matters | Complex work requiring discussion & collaboration |
| **Token cost** | Lower (results summarized back) | Higher (each teammate is a separate Claude instance) |

**Rule of thumb**: use subagents when you need quick workers that report back. Use agent teams when teammates need to share findings, challenge each other, and coordinate on their own.

---

## When to Use Agent Teams

### Strong Use Cases

- **Research and review**: multiple teammates investigate different aspects simultaneously, then share and challenge findings
- **New modules or features**: teammates each own a separate piece without stepping on each other
- **Debugging with competing hypotheses**: test different theories in parallel, converge faster
- **Cross-layer coordination**: frontend, backend, and tests each owned by a different teammate

### When NOT to Use

- Sequential tasks with dependencies between steps
- Same-file edits (causes overwrites)
- Routine or simple tasks (coordination overhead exceeds benefit)
- Work where a single session or subagent is sufficient

---

## Setup

### 1. Enable the Feature

Agent teams are experimental and disabled by default. Add to your `settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Or set as environment variable:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### 2. Display Mode (Optional)

Configure how teammates appear. Add to `settings.json`:

```json
{
  "teammateMode": "in-process"
}
```

Options:
- `"auto"` (default) — uses split panes if inside tmux, in-process otherwise
- `"in-process"` — all teammates run in your main terminal
- `"tmux"` — each teammate gets its own pane (requires tmux or iTerm2)

Override per session:

```bash
claude --teammate-mode in-process
```

---

## Keyboard Controls

| Shortcut | Action |
|---|---|
| **Shift+Up/Down** | Cycle through teammates (in-process mode) |
| **Shift+Tab** | Toggle delegate mode (lead coordinates only, no coding) |
| **Ctrl+T** | Toggle the shared task list |
| **Enter** | View a teammate's session |
| **Escape** | Interrupt a teammate's current turn |

In split-pane mode, click into a teammate's pane to interact directly.

---

## Architecture

| Component | Role |
|---|---|
| **Team lead** | Main session that creates team, spawns teammates, coordinates |
| **Teammates** | Separate Claude Code instances working on assigned tasks |
| **Task list** | Shared work items with dependency tracking and file-lock claiming |
| **Mailbox** | Messaging system for inter-agent communication |

Storage:
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

---

## Prompt Templates

### Code Review (Parallel Multi-Perspective)

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

### New Feature Development (Cross-Layer)

```
Create an agent team to implement the user notification system:
- One teammate owns the domain model and service layer (src/domain/, src/service/)
- One teammate owns the API controllers and DTOs (src/api/, src/dto/)
- One teammate owns the tests (src/test/)
Each teammate should only modify files in their assigned directories.
```

### Debugging with Competing Hypotheses

```
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
```

### Research and Exploration

```
I'm designing a CLI tool that helps developers track TODO comments across
their codebase. Create an agent team to explore this from different angles:
- One teammate on UX and developer experience
- One on technical architecture and implementation
- One playing devil's advocate, finding flaws in the others' proposals
```

### Refactoring with Plan Approval

```
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
Only approve plans that include test coverage and maintain backward compatibility.
```

### Library/Technology Evaluation

```
Create an agent team to evaluate state management options for our React app:
- One teammate researches Redux Toolkit
- One teammate researches Zustand
- One teammate researches Jotai
Each should build a small proof of concept and report trade-offs.
Have them challenge each other's conclusions.
```

### Specifying Models and Team Size

```
Create a team with 4 teammates to refactor these modules in parallel.
Use Sonnet for each teammate.
```

---

## Best Practices

### 1. Give Teammates Rich Context

Teammates load project context (CLAUDE.md, MCP servers, skills) but **don't inherit the lead's conversation history**. Be specific:

```
Spawn a security reviewer teammate with the prompt: "Review the authentication
module at src/auth/ for security vulnerabilities. Focus on token handling, session
management, and input validation. The app uses JWT tokens stored in httpOnly
cookies. Report any issues with severity ratings."
```

### 2. Size Tasks Appropriately

- **Too small**: coordination overhead exceeds the benefit
- **Too large**: teammates work too long without check-ins, risk of wasted effort
- **Just right**: self-contained units that produce a clear deliverable (a function, a test file, a review)
- Aim for **5-6 tasks per teammate** to keep everyone productive

### 3. Avoid File Conflicts

Break work so **each teammate owns different files**. Two teammates editing the same file leads to overwrites. Assign clear directory/file boundaries.

### 4. Use Delegate Mode

Press **Shift+Tab** to prevent the lead from implementing tasks itself. The lead focuses purely on:
- Spawning teammates
- Messaging and coordinating
- Managing tasks
- Synthesizing results

### 5. Use Plan Approval for Risky Work

```
Spawn a teammate to refactor the payment module.
Require plan approval before they make any changes.
Reject plans that modify the database schema without a migration.
```

### 6. Keep the Lead Waiting

The lead sometimes starts implementing instead of delegating. Correct it:

```
Wait for your teammates to complete their tasks before proceeding.
```

### 7. Start with Read-Only Tasks

If new to agent teams, begin with tasks that don't write code:
- Reviewing a PR
- Researching a library
- Investigating a bug
- Evaluating architectural options

### 8. Monitor and Steer

Check in on progress, redirect failing approaches, and don't let teams run unattended too long.

### 9. Pre-Approve Permissions

Teammate permission requests bubble up to the lead, creating friction. Pre-approve common operations in your permission settings before spawning teammates.

---

## Lifecycle

### Starting

```
Create an agent team to [describe task and team structure]
```

Claude creates the team, spawns teammates, and coordinates based on your prompt. Claude may also propose a team if it thinks your task would benefit — you confirm before it proceeds.

### During Work

- Tasks flow through: **pending** → **in progress** → **completed**
- Tasks can have dependencies (blocked until dependencies complete)
- Teammates self-claim available tasks after finishing their current one
- The lead can assign tasks explicitly or let teammates self-organize

### Shutting Down

Shut down individual teammates:

```
Ask the researcher teammate to shut down.
```

Clean up the entire team (always do this from the lead):

```
Clean up the team.
```

Shut down all teammates before cleanup — it fails if any are still running.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Teammates not appearing | Press Shift+Down to cycle. Check task complexity warrants a team. |
| Too many permission prompts | Pre-approve common operations in permission settings. |
| Teammates stopping on errors | Message them directly with instructions, or spawn a replacement. |
| Lead shuts down too early | Tell it to wait for teammates to finish. |
| Orphaned tmux sessions | `tmux ls` then `tmux kill-session -t <session-name>` |
| Task appears stuck | Check if work is done but status wasn't updated. Nudge the teammate. |

---

## Limitations

- **Experimental** — disabled by default, expect rough edges
- **No session resumption** — `/resume` and `/rewind` don't restore in-process teammates
- **Task status can lag** — teammates sometimes forget to mark tasks done
- **One team per session** — clean up before starting a new team
- **No nested teams** — teammates can't spawn their own teams
- **Lead is fixed** — can't promote a teammate or transfer leadership
- **Permissions set at spawn** — all teammates inherit the lead's mode; change individually after
- **Split panes** — don't work in VS Code terminal, Windows Terminal, or Ghostty
- **Token cost** — scales significantly with team size; use only when the parallelism justifies it
