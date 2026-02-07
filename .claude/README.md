# Claude Skills & Configuration

This directory contains **Skills** for Claude to dynamically load domain-specific expertise on-demand, preventing context window bloat while providing specialized guidance.

## What are Skills?

Skills are markdown documents containing:
- Domain-specific instructions and best practices
- Code examples and patterns
- Prohibited anti-patterns
- Decision-making frameworks

When Claude detects a task matching a skill's domain (e.g., "build a React component", "create a database migration"), it automatically loads that skill's context just-in-time.

**Key Benefits:**
- ✅ No permanent context overhead
- ✅ Domain expertise activated only when needed
- ✅ Consistent patterns across the codebase
- ✅ Reusable and version-controlled knowledge

## Skills vs Plugins

This directory uses **Skills** (not Plugins):

| Skills | Plugins |
|--------|---------|
| 📚 Instructions & Knowledge | 🔌 Executable Functionality |
| Markdown files (`SKILL.md`) | JSON + scripts (`plugin.json`) |
| Guide Claude's thinking | Extend Claude's actions |
| Auto-activated by context | Explicit commands |
| What you have ✅ | Future enhancement |

**See `SKILLS_VS_PLUGINS_COMPLETE_GUIDE.md` for detailed comparison.**

## Skills Directory Structure

```
.claude/
├── skills/
│   ├── frontend-design/
│   │   └── SKILL.md              # UI/UX aesthetics & modern design
│   ├── design-decisions-copilot/
│   │   └── SKILL.md              # Interactive decision-making for architecture
│   ├── kotlin-backend-architecture/
│   │   └── SKILL.md              # SOLID principles, clean architecture, TDD
│   ├── react-state-management/
│   │   └── SKILL.md              # React hooks, context, React Query patterns
│   ├── api-integration/
│   │   └── SKILL.md              # HTTP clients, error handling, retries
│   └── database-migrations/
│       └── SKILL.md              # Flyway migrations, schema evolution
├── settings.local.json           # Permissions configuration
├── README.md                     # This file
├── SKILLS_ANALYSIS_AND_RECOMMENDATIONS.md  # Skills usage examples
└── SKILLS_VS_PLUGINS_COMPLETE_GUIDE.md    # Skills vs Plugins explained
```

## Available Skills

### 1. **Frontend Design** (`frontend-design`)
**When activated:** Building web components, pages, or applications

**What it provides:**
- Distinctive aesthetics avoiding "AI slop" (no Inter/Roboto, purple gradients)
- Typography principles (use interesting fonts like JetBrains Mono, Playfair Display)
- Motion and animations (scroll-triggered, staggered reveals)
- Background effects (gradient meshes, noise textures, layered transparencies)
- Theme commitment (bold aesthetic decisions)

**Example activation:**
> "Create a landing page for our tax automation platform"

---

### 2. **Design Decisions Copilot** (`design-decisions-copilot`)
**When activated:** Making architectural or product decisions

**What it provides:**
- Interactive question-driven dialogue
- Multiple options with pros/cons and tradeoffs
- Decision logging and documentation
- Risk assessments for critical decisions

**Example activation:**
> "Help me decide between monolith vs microservices for our backend"

---

### 3. **Kotlin Backend Architecture** (`kotlin-backend-architecture`)
**When activated:** Implementing backend APIs, domain models, or infrastructure

**What it provides:**
- SOLID principles application
- Clean architecture layers (Domain → Application → Infrastructure)
- Constructor dependency injection
- Test-Driven Development (TDD) with Arrange-Act-Assert
- Value objects for domain primitives
- Repository patterns and Spring Boot best practices

**Example activation:**
> "Implement a CompanyService with CRUD operations"

---

### 4. **React State Management** (`react-state-management`)
**When activated:** Building React components with state

**What it provides:**
- State colocation and lifting principles
- React Query for server state (caching, refetching)
- Custom hooks for reusable logic
- useReducer for complex state
- Performance optimization (useMemo, useCallback, lazy loading)
- Zustand for global state
- Form handling with React Hook Form + Zod

**Example activation:**
> "Create a form to create companies with validation"

---

### 5. **API Integration** (`api-integration`)
**When activated:** Implementing HTTP clients or external service integrations

**What it provides:**
- Centralized API client configuration (Axios interceptors)
- Typed service layer classes
- Comprehensive error handling (ApiError classes)
- Retry logic with exponential backoff
- Request cancellation on component unmount
- React Query integration for caching
- Optimistic updates and rollback
- File upload with progress tracking
- Security best practices (CSRF, input validation)

**Example activation:**
> "Create an API client for the companies endpoint"

---

### 6. **Database Migrations** (`database-migrations`)
**When activated:** Creating or modifying database schema

**What it provides:**
- Flyway migration naming conventions (V{version}__{description}.sql)
- Idempotent migrations (IF NOT EXISTS)
- Forward/backward compatibility patterns
- Multi-step zero-downtime deployments
- Strategic indexing
- Data integrity constraints
- Large data migration batching
- Testing strategies with Testcontainers

**Example activation:**
> "Add a new column 'industry' to the companies table"

---

## How Skills Work

### Automatic Activation
Claude reads the task context and activates relevant skills:

```
User: "Build a company registration form"
     ↓
Claude activates:
  - react-state-management (form logic)
  - frontend-design (UI aesthetics)
  - api-integration (submit to backend)
```

### Manual Activation
You can explicitly request a skill:

```
User: "Using the kotlin-backend-architecture skill, refactor this service"
```

### Skills Compose
Multiple skills can work together:

```
User: "Implement user authentication"
     ↓
Claude might use:
  - kotlin-backend-architecture (backend AuthService)
  - api-integration (frontend auth API client)
  - react-state-management (user state management)
  - database-migrations (users table creation)
```

## Creating New Skills

### Skill File Template

```markdown
---
name: skill-name
description: One-line description of when to use this skill
---

# Skill Name

## Overview
Brief explanation of the skill's purpose.

## When to Use This Skill

Activate when the user:
- Describes scenario 1
- Asks about topic 2
- Works on feature 3

## Core Principles

### 1. Principle Name

Explanation and examples:

\`\`\`language
// ✅ GOOD - Example of good practice
code here

// ❌ BAD - Example of anti-pattern
code here
\`\`\`

## Remember

- Key takeaway 1
- Key takeaway 2
- Key takeaway 3
```

### Best Practices for Skill Creation

1. **Be Specific:** Provide concrete examples, not abstract theory
2. **Show Good vs Bad:** Use ✅ and ❌ to highlight patterns
3. **Map to Code:** Aesthetic concepts should translate to implementable code
4. **Right Altitude:** Not too low-level (hardcoded values) or too high-level (vague guidance)
5. **Domain Boundaries:** Keep skills focused on one domain
6. **Actionable:** Every principle should be implementable immediately

## Configuration Files

### `settings.local.json`
Defines permissions for commands and tools Claude can use:

```json
{
  "permissions": {
    "allow": [
      "WebSearch",
      "Bash(./gradlew clean build:*)",
      "mcp__playwright__browser_navigate"
    ],
    "deny": [],
    "ask": []
  }
}
```

**Permission Patterns:**
- `WebSearch` - Allow web searches
- `Bash(command:*)` - Allow specific bash commands with wildcards
- `mcp__*` - Allow MCP (Model Context Protocol) tool usage

### Note on Plugins

**Plugins** are a separate system from **Skills**:
- **Skills** = Instructions/knowledge (what you have)
- **Plugins** = Executable tools/integrations (optional add-on)

Your current `plugins/frontend-design/plugin.json` contains only metadata without executable functionality. 

**Recommendation:** Remove the `plugins/` directory for now. If you later need executable functionality (deployment scripts, external integrations, etc.), you can create proper plugins with actual code.

See `SKILLS_VS_PLUGINS_COMPLETE_GUIDE.md` for complete details.

## Related Resources

- [Anthropic Blog: Improving Frontend Design Through Skills](https://www.claude.com/blog/improving-frontend-design-through-skills)
- [Claude Documentation](https://docs.anthropic.com/)

## Maintenance

### When to Update Skills

- ✅ New patterns emerge in the codebase
- ✅ Team adopts new libraries or frameworks
- ✅ Anti-patterns are discovered and need documentation
- ✅ Best practices evolve

### Version Control

All skills are version-controlled in Git. Changes should be:
1. Reviewed by team
2. Tested with Claude to ensure effectiveness
3. Documented in commit messages

---

**Note:** Skills are designed to **complement** your existing coding standards and rules (defined in `.cursorrules` or similar). They provide tactical, hands-on guidance for specific domains, while higher-level principles (like "always use TDD" or "follow SOLID") remain in your global rules.

