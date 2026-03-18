# Showcase Version Plan for Personalized AI Agent

## Purpose

This document defines a five-version showcase roadmap built on top of Persbot for the group project:

`Personalization of Large Language Models: Towards True AI Assistant, Mentor and Companion`

The roadmap is designed for group meetings and demos. Each version:

- has a visible UI or behavior difference
- advances the system as an integrated product
- gives all six members concrete contributions to present

## Hard Requirements for Every Version

Every version must satisfy all three conditions below. If one is missing, the version is not considered demo-ready.

1. Visual Difference
   The audience must be able to see at least one obvious new page, panel, workflow step, or system state on screen.
2. Behavioral Difference
   The agent must do at least one thing in demo that the previous version could not do.
3. Verbal Difference
   The presenter must be able to describe the version upgrade in one short sentence starting with:
   `Compared with V{n-1}, V{n} now can ...`

## Demo Design Rule

To avoid weak iterations, each version should introduce:

- one new visible page or panel
- one new end-user interaction step
- one new agent capability that can be demonstrated live
- one short spoken upgrade line for the whole group
- one short spoken contribution line for each member

## Progress Allocation

| Version | Progress Share | Position in Roadmap |
| --- | ---: | --- |
| V1 | 25% | Integrated PoC |
| V2 | 18.75% | Memory Growth |
| V3 | 18.75% | Mentor Loop |
| V4 | 18.75% | Action Loop |
| V5 | 18.75% | Trustworthy Organism |

## Member Mapping

| Member | Module |
| --- | --- |
| Yi Ding | Cognitive Engine |
| Jinchang Zhu | Agent Memory System |
| Chenghao Wu | Semantic-Aware Recommendation |
| Xiaojian Nie | Visual Workflow Learning |
| Ying Liu | Alignment Module |
| Yaxin Li | Security and Privacy Framework |

## V1: Integrated PoC

### Demo Goal

Show the system as a complete product shell instead of a generic bot. The user can:

- enter the system through a dedicated Personalized AI Agent homepage
- choose `Assistant`, `Mentor`, or `Companion` mode
- create a profile with goals and preferences
- chat with the agent
- see module entry points for memory, recommendation, workflow, and trust

### Visible Differences

- new homepage and project branding
- new sidebar structure
- profile panel
- three-mode agent switcher
- placeholder but functional pages for Memory, Recommendation, Workflow, and Trust Center

### What Must Be Obvious in Demo

- this is no longer a generic bot UI
- the system now has a personalized product shell
- the audience can already see all major modules in the navigation

### Whole-Group Upgrade Line

`V1 turns Persbot from a general chatbot backend into a visible Personalized AI Agent product shell.`

### Presenter Script Anchor

`Compared with the original base system, V1 now gives us a unified personalized interface with profile, modes, and module entry points.`

### Member Contributions

| Member | Specific Work in V1 |
| --- | --- |
| Yi Ding | Build the multi-mode reasoning entry and basic prompt routing for Assistant, Mentor, and Companion. |
| Jinchang Zhu | Define the initial user profile schema and minimal memory write/read loop. |
| Chenghao Wu | Build the recommendation page V0 and generate first-pass suggestion cards from user goals. |
| Xiaojian Nie | Build the workflow shell page and task panel entry for later action demos. |
| Ying Liu | Add baseline safety response strategy, risk labels, and refusal policy. |
| Yaxin Li | Build authentication entry, basic privacy settings, and access-control surfaces. |

### Member Speaking Lines

- Yi Ding: `In V1, I turned a generic response pipeline into three user-facing agent modes.`
- Jinchang Zhu: `In V1, I added the first structured user profile and memory entry point.`
- Chenghao Wu: `In V1, I exposed recommendation as a visible part of the product rather than a hidden future idea.`
- Xiaojian Nie: `In V1, I prepared the workflow interface so execution can become demonstrable in later versions.`
- Ying Liu: `In V1, I made safety visible from the first version instead of treating it as a backend-only concern.`
- Yaxin Li: `In V1, I added the basic privacy and access-control surfaces needed for a personalized system.`

## V2: Memory Growth

### Demo Goal

Show that the system remembers the user across sessions and organizes that memory into usable structures.

### Visible Differences

- memory timeline page
- semantic summary panel
- recalled memory tags shown in replies
- memory edit and delete controls

### Demo Scenario

The user returns in a later session. The system recalls prior goals, preferences, or tasks and explains which memories were used.

### What Must Be Obvious in Demo

- the system remembers the user across sessions
- the UI now exposes memory as editable, inspectable, and structured
- replies visibly cite remembered facts or goals

### Whole-Group Upgrade Line

`V2 upgrades the shell into a memory-aware agent that can persist and recall user context.`

### Presenter Script Anchor

`Compared with V1, V2 now remembers past sessions and organizes memory into a visible timeline and summary view.`

### Member Contributions

| Member | Specific Work in V2 |
| --- | --- |
| Yi Ding | Make reasoning consume recalled memory rather than only current-turn context. |
| Jinchang Zhu | Implement episodic and semantic memory organization, retrieval, and consolidation. |
| Chenghao Wu | Connect recommendation logic to memory tags and long-term interests. |
| Xiaojian Nie | Write workflow logs into the memory timeline as behavioral history. |
| Ying Liu | Add conflict detection, low-confidence memory warnings, and correction flow. |
| Yaxin Li | Add sensitive-memory visibility controls, export, and delete operations. |

### Member Speaking Lines

- Yi Ding: `In V2, I made the reasoning chain consume recalled memory instead of only the current chat turn.`
- Jinchang Zhu: `In V2, I implemented the actual episodic and semantic memory structure.`
- Chenghao Wu: `In V2, I made recommendation depend on remembered long-term interests.`
- Xiaojian Nie: `In V2, I connected workflow history to memory so the system can remember behavior, not just text.`
- Ying Liu: `In V2, I added conflict and confidence control so memory is not blindly trusted.`
- Yaxin Li: `In V2, I made sensitive memory visible and controllable through privacy operations.`

## V3: Mentor Loop

### Demo Goal

Show proactive guidance instead of only reactive answering.

### Visible Differences

- recommendation page
- goal board
- explanation area for why something is recommended
- feedback controls such as useful, not useful, and refine

### Demo Scenario

The user asks about a research direction. The system proposes next steps, papers, or learning paths based on profile and memory.

### What Must Be Obvious in Demo

- the system now gives proactive suggestions
- there is a dedicated recommendation view
- the agent can explain why a suggestion is relevant to this user

### Whole-Group Upgrade Line

`V3 upgrades the memory-aware agent into a mentor-style system that can proactively guide the user.`

### Presenter Script Anchor

`Compared with V2, V3 now does not just remember the user, it proactively recommends what the user should do next.`

### Member Contributions

| Member | Specific Work in V3 |
| --- | --- |
| Yi Ding | Add goal decomposition and mentor-style reasoning behavior. |
| Jinchang Zhu | Feed long-term interests, goals, and historical preferences back into the profile and memory layers. |
| Chenghao Wu | Implement ranking, recommendation rationale, and user feedback loop. |
| Xiaojian Nie | Add the interaction that converts a recommendation into an executable task. |
| Ying Liu | Add anti-overrecommendation rules, confidence gating, and interruption control. |
| Yaxin Li | Constrain recommendation data access and expose privacy boundaries for recommendation logs. |

### Member Speaking Lines

- Yi Ding: `In V3, I added goal decomposition so the agent can mentor instead of only answer.`
- Jinchang Zhu: `In V3, I fed long-term user interests and goals back into the recommendation loop.`
- Chenghao Wu: `In V3, I built the ranking logic and explanation for proactive recommendations.`
- Xiaojian Nie: `In V3, I let users turn a recommendation directly into an executable task.`
- Ying Liu: `In V3, I controlled recommendation quality and interruption frequency to keep mentoring useful.`
- Yaxin Li: `In V3, I constrained what personal data the recommendation engine can access and expose.`

## V4: Action Loop

### Demo Goal

Show that the system can turn intention into execution and expose the process to the user.

### Visible Differences

- workflow studio
- execution trace panel
- task replay panel
- action cards created from recommendation or chat

### Demo Scenario

The user clicks a suggested task. The system decomposes the task, executes tools or workflow steps, and shows the trace and replay.

### What Must Be Obvious in Demo

- the system can now execute rather than only suggest
- the UI shows a workflow studio and execution trace
- the task can be replayed or inspected step by step

### Whole-Group Upgrade Line

`V4 upgrades the mentor into an action-capable assistant that can turn advice into execution.`

### Presenter Script Anchor

`Compared with V3, V4 now converts recommendations and intentions into visible executable workflows.`

### Member Contributions

| Member | Specific Work in V4 |
| --- | --- |
| Yi Ding | Implement task planning and decomposition from high-level intent to concrete steps. |
| Jinchang Zhu | Store task history, success and failure patterns, and reusable execution memory. |
| Chenghao Wu | Recommend the next best action based on current workflow state. |
| Xiaojian Nie | Implement workflow execution, parameter display, replay, and retry support. |
| Ying Liu | Add step-level confirmation, high-risk action interception, and rollback guidance. |
| Yaxin Li | Add sandbox boundaries, file permissions, tool permissions, and action audit controls. |

### Member Speaking Lines

- Yi Ding: `In V4, I implemented planning so the system can break a goal into executable steps.`
- Jinchang Zhu: `In V4, I stored task outcomes as reusable execution memory.`
- Chenghao Wu: `In V4, I recommended the next best action based on workflow state.`
- Xiaojian Nie: `In V4, I implemented the actual workflow execution, replay, and retry interface.`
- Ying Liu: `In V4, I added interception and rollback guidance for risky actions.`
- Yaxin Li: `In V4, I put execution inside explicit permission and sandbox boundaries.`

## V5: Trustworthy Organism

### Demo Goal

Show the complete integrated system as a trustworthy personalized AI agent.

### Visible Differences

- unified system overview dashboard
- trust center
- alignment panel
- security center
- audit log

### Demo Scenario

The system uses profile and memory to make a proactive recommendation, converts it into an action, requests confirmation on a risky step, and records the decision in the audit log.

### What Must Be Obvious in Demo

- all major modules now appear integrated in one end-to-end flow
- trust, alignment, and security are visible as first-class interfaces
- the system can justify and log risky decisions

### Whole-Group Upgrade Line

`V5 upgrades the action-capable assistant into a trustworthy personalized AI organism with visible governance.`

### Presenter Script Anchor

`Compared with V4, V5 now closes the loop with alignment, security, and auditability, making the full personalized agent trustworthy.`

### Member Contributions

| Member | Specific Work in V5 |
| --- | --- |
| Yi Ding | Integrate unified orchestration across Assistant, Mentor, and Companion modes. |
| Jinchang Zhu | Add long-term user summary, memory health, and consolidation views. |
| Chenghao Wu | Build a proactive panel that aggregates personalized next steps. |
| Xiaojian Nie | Connect the final end-to-end workflow and demo replay path. |
| Ying Liu | Build the alignment dashboard, risk grading, and intervention explanations. |
| Yaxin Li | Build the security center, permission overview, privacy controls, and audit log. |

### Member Speaking Lines

- Yi Ding: `In V5, I unified the orchestration across Assistant, Mentor, and Companion behaviors.`
- Jinchang Zhu: `In V5, I exposed long-term summary and memory health as a stable user-facing capability.`
- Chenghao Wu: `In V5, I aggregated personalized next steps into a proactive decision panel.`
- Xiaojian Nie: `In V5, I connected the full end-to-end demo path from suggestion to execution replay.`
- Ying Liu: `In V5, I made alignment visible through intervention reasons and risk grades.`
- Yaxin Li: `In V5, I made trust concrete with security center, privacy controls, and audit logs.`

## Worktree Mapping

| Version | Branch | Worktree Path |
| --- | --- | --- |
| V1 | `showcase/v1-integrated-poc` | `/Users/h1syu1/PythonProjects/AstrBot/.showcase-worktrees/v1-integrated-poc` |
| V2 | `showcase/v2-memory-growth` | `/Users/h1syu1/PythonProjects/AstrBot/.showcase-worktrees/v2-memory-growth` |
| V3 | `showcase/v3-mentor-loop` | `/Users/h1syu1/PythonProjects/AstrBot/.showcase-worktrees/v3-mentor-loop` |
| V4 | `showcase/v4-action-loop` | `/Users/h1syu1/PythonProjects/AstrBot/.showcase-worktrees/v4-action-loop` |
| V5 | `showcase/v5-trustworthy-organism` | `/Users/h1syu1/PythonProjects/AstrBot/.showcase-worktrees/v5-trustworthy-organism` |

## Notes for Group Meetings

- Every version should keep one stable demo script.
- Every version should include at least one new page or panel that is visually obvious.
- Every member should speak from the perspective of integration, not isolated modules.
- The project story should progress as: shell, memory, mentor, action, trust.
- The audience should be able to answer two questions after each demo:
  `What can this version do that the last one could not?`
  `Which screen or behavior proves that upgrade?`
