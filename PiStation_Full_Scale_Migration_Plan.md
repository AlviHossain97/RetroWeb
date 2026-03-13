# PiStation Full-Scale Migration Plan
## Convert the Existing React Emulator App into a PiStation Dashboard Platform
## With FastAPI/MySQL Backend, AI Database Access, and Full Controller Compatibility

---

# 1. Executive Summary

This migration plan transforms the current browser-emulator React application into a **PiStation platform** that uses:

- **React + TypeScript + Vite** as the frontend shell
- **FastAPI** as the backend/API layer
- **MySQL** as the source of truth
- **Laptop-hosted execution** for all heavy logic
- **Raspberry Pi as a fullscreen thin client**
- **AI features retained and upgraded**
- **Controller-first navigation with optional virtual cursor**
- **Mouse and keyboard support preserved**

The end result is a modern dashboard platform that can:

- show live and historical gaming activity
- support controller navigation like a console UI
- answer database-backed AI questions about users, games, sessions, and trends
- run entirely on the laptop while displaying on the Pi
- scale into a polished final year project deliverable

---

# 2. Core Objective

Migrate the existing emulator-style web app into a **PiStation Hub** without wasting the strongest parts of the original app.

## New product goals

The new system should become a multi-purpose PiStation dashboard that supports:

- dashboard overview
- live session display
- recent sessions
- game analytics
- per-system analytics
- per-device monitoring
- AI assistant with database-aware answers
- controller diagnostics and remapping
- achievement tracking
- settings and accessibility controls
- kiosk mode for EmulationStation / TV display

---

# 3. High-Level Strategy

This should **not** be treated as a simple redesign.

It should be treated as a **staged migration** with these principles:

1. **Keep the frontend shell**
2. **Remove browser-emulation logic**
3. **Replace local-first storage with backend-first APIs**
4. **Preserve and upgrade the AI layer**
5. **Add controller-first interaction**
6. **Use the Pi only as a display client**
7. **Make the backend the source of truth**

The correct mental model is:

- **Frontend transplant**
- **Backend consolidation**
- **AI grounding**
- **Controller UX redesign**
- **Pi kiosk optimisation**

---

# 4. Target End-State Architecture

## 4.1 Laptop responsibilities

The laptop should run:

- FastAPI backend
- MySQL database
- React frontend dev/build server
- AI inference services
- analytics logic
- controller profile persistence
- safe AI tooling layer
- metadata services
- optional voice stack (Whisper + Kokoro + Ollama)

## 4.2 Raspberry Pi responsibilities

The Pi should only:

- launch a browser
- load the dashboard from the laptop
- display a fullscreen kiosk route
- handle controller input locally in the browser
- optionally provide device heartbeat data

This turns the Pi into a thin client and avoids making the Pi 3 do heavy backend work.

## 4.3 Core interaction flow

1. RetroPie launches a browser
2. Browser loads laptop-hosted dashboard
3. Dashboard fetches data from FastAPI
4. FastAPI queries MySQL
5. AI requests go through FastAPI orchestration
6. Safe tools query allowed analytics data
7. AI returns grounded answers
8. Controller input drives focus navigation or virtual cursor

---

# 5. What to Keep, Replace, and Remove

## 5.1 Keep

These parts are worth preserving from the current app:

- React + TypeScript + Vite setup
- app shell and route structure
- Tailwind/shadcn styling system
- theme system
- Zustand stores for app/UI state
- lazy-loaded route pattern
- chat page concept
- controller diagnostics concept
- achievements concept
- settings pages
- reusable cards, panels, layouts, and shell components
- page transition and feedback patterns where lightweight
- accessibility helpers

## 5.2 Replace

These should be replaced with backend-integrated equivalents:

- Dexie / IndexedDB as source of truth
- ROM/game state stored only locally
- local-only stats aggregation
- local AI persistence
- current session bootstrapping assumptions
- route logic tightly coupled to emulator state
- client-side gameplay-first navigation model
- fake auth/session gate

## 5.3 Remove entirely

These systems should be cut:

- browser emulation runtime
- Nostalgist or equivalent WASM emulator integration
- OPFS ROM storage
- BIOS management
- browser save states
- browser-based ROM launching
- netplay runtime
- emulator canvas gameplay route
- upload/import flows dedicated to in-browser emulation

These features can inspire UI decisions, but their code paths should not remain active in the migrated platform.

---

# 6. New Product Information Architecture

## 6.1 Primary routes

The new frontend should evolve into these key routes:

- `/` → Home dashboard
- `/dashboard` → main analytics dashboard
- `/dashboard/kiosk` → fullscreen TV/Pi mode
- `/sessions` → live and historical sessions
- `/games` → game analytics and library view
- `/systems` → per-platform analytics
- `/devices` → Pi/device health and status
- `/players` → user-centric analytics (later)
- `/chat` → AI assistant
- `/controller` → controller setup and testing
- `/achievements` → badges, milestones, streaks
- `/settings` → preferences and accessibility
- `/admin` → diagnostics, logs, maintenance
- `/login` → only when proper auth is added

## 6.2 Page purpose mapping

### Home
Overview surface:
- now playing
- active devices
- sessions today
- total playtime today
- recent sessions
- quick AI actions
- favourite system / game
- trending activity

### Sessions
For timeline and detail:
- active sessions
- recent sessions
- filters by date/system/game/user/device
- abnormal session detection
- duration breakdowns

### Games
For analytics rather than ROM launching:
- searchable game list
- per-game summary pages
- last played
- total time played
- play frequency
- favourite status
- artwork
- related recommendations

### Systems
Per-console/platform insights:
- time spent by system
- number of sessions
- top games by system
- trends over time
- platform-specific favourites

### Devices
Operational monitoring:
- Pi hostname
- last heartbeat
- online/offline state
- current session
- display status
- browser health
- app version
- network stats if desired

### Chat
AI assistant:
- general support
- stats questions
- recommendations
- trend summaries
- voice I/O
- database-aware answers

### Controller
Controller layer:
- device detection
- input visualisation
- remapping
- focus navigation settings
- virtual cursor settings
- deadzones and sensitivity
- mode switching

### Achievements
Motivation system:
- unlocked achievements
- progress to next milestones
- streaks
- categories
- per-user or global unlocks

### Settings
System and user preferences:
- theme
- display density
- accessibility
- audio
- AI settings
- controller settings
- keyboard/mouse settings
- kiosk preferences

### Admin
Support and diagnostics:
- DB status
- API health
- device health
- queued events
- AI usage
- errors/logs
- version/build info

---

# 7. Frontend Migration Plan

## 7.1 Frontend target structure

```text
frontend/
  src/
    app/
      router.tsx
      providers.tsx
      layout/
        AppShell.tsx
        KioskShell.tsx
    components/
      dashboard/
      sessions/
      games/
      systems/
      devices/
      chat/
      controller/
      achievements/
      settings/
      kiosk/
      common/
      ui/
    pages/
      HomePage.tsx
      DashboardPage.tsx
      KioskDashboardPage.tsx
      SessionsPage.tsx
      SessionDetailPage.tsx
      GamesPage.tsx
      GameDetailPage.tsx
      SystemsPage.tsx
      DevicesPage.tsx
      ChatPage.tsx
      ControllerPage.tsx
      AchievementsPage.tsx
      SettingsPage.tsx
      AdminPage.tsx
    hooks/
      usePolling.ts
      useSSE.ts
      useGamepadNavigation.ts
      useFocusGraph.ts
      useVirtualCursor.ts
      useInputMode.ts
    lib/
      api/
        client.ts
        dashboard.ts
        sessions.ts
        games.ts
        systems.ts
        devices.ts
        ai.ts
        controller.ts
        achievements.ts
      utils/
      constants/
      types/
    stores/
      appStore.ts
      dashboardStore.ts
      aiStore.ts
      controllerStore.ts
      settingsStore.ts
      kioskStore.ts
```

## 7.2 Frontend migration phases

### Phase A — Stabilise the shell
- ensure the app still boots after emulator removal
- preserve app shell and route navigation
- remove broken imports progressively
- keep placeholder routes for removed features until replacements exist

### Phase B — Create API-first data layer
- add a shared HTTP client
- add typed response models
- build service modules per domain
- centralise error handling
- add loading and empty states

### Phase C — Convert core pages
- Home
- Dashboard
- Sessions
- Games
- Systems
- Devices

### Phase D — Restore advanced features
- Chat
- Controller
- Achievements
- Settings
- Admin

### Phase E — Add kiosk mode
- fullscreen layout
- TV-friendly sizing
- controller-first navigation
- reduced motion
- simplified chrome

---

# 8. Backend Migration Plan

## 8.1 Backend target structure

```text
backend/
  app/
    main.py
    config.py
    db.py
    dependencies.py
    models/
    schemas/
    routes/
      health.py
      dashboard.py
      sessions.py
      games.py
      systems.py
      devices.py
      ai.py
      achievements.py
      controller.py
      settings.py
      admin.py
    services/
      session_service.py
      stats_service.py
      dashboard_service.py
      game_service.py
      system_service.py
      device_service.py
      ai_service.py
      ai_tools_service.py
      ai_sql_service.py
      controller_service.py
      achievement_service.py
      metadata_service.py
      audit_service.py
    repos/
      session_repo.py
      game_repo.py
      system_repo.py
      device_repo.py
      stats_repo.py
      achievement_repo.py
      ai_repo.py
      controller_repo.py
    migrations/
```

## 8.2 Backend priorities

### Immediate
- health endpoint
- dashboard summary endpoint
- active/recent sessions endpoints
- games and systems list endpoints
- devices list endpoint
- AI chat endpoint scaffold

### Next
- per-game detail endpoints
- per-system detail endpoints
- heartbeat endpoint
- controller profile endpoints
- achievements endpoints

### Later
- authentication
- user profiles
- voice processing pipeline
- admin diagnostics expansion
- AI query auditing
- recommendation services

---

# 9. Database Migration Plan

## 9.1 Core database principle

MySQL becomes the authoritative source of truth for:

- sessions
- games
- devices
- users
- AI interactions
- controller profiles
- achievements
- aggregates

The frontend should never be treated as authoritative for platform analytics.

## 9.2 Recommended schema

### devices
- id
- hostname
- display_name
- ip_address
- status
- last_seen_at
- client_version
- notes
- created_at
- updated_at

### users
- id
- username
- email
- display_name
- avatar_url
- password_hash (when auth added)
- created_at
- updated_at

### games
- id
- canonical_title
- rom_path
- rom_hash
- system_name
- emulator
- core
- cover_url
- description
- metadata_json
- created_at
- updated_at

### sessions
- id
- game_id
- device_id
- user_id nullable
- started_at
- ended_at nullable
- duration_seconds nullable
- status
- source_event_id
- raw_payload_json
- created_at
- updated_at

### session_events
- id
- session_id nullable
- device_id
- event_type
- dedupe_key
- payload_json
- created_at

### daily_game_stats
- date
- game_id
- total_seconds
- session_count
- unique_devices

### daily_system_stats
- date
- system_name
- total_seconds
- session_count
- unique_devices

### achievements
- id
- code
- title
- description
- icon
- category
- created_at

### user_achievements
- id
- user_id
- achievement_id
- unlocked_at
- context_json

### controller_profiles
- id
- user_id nullable
- device_id nullable
- profile_name
- mapping_json
- cursor_settings_json
- navigation_settings_json
- created_at
- updated_at

### ai_conversations
- id
- user_id nullable
- device_id nullable
- title
- created_at
- updated_at

### ai_messages
- id
- conversation_id
- role
- content
- metadata_json
- created_at

### ai_query_audit
- id
- conversation_id nullable
- question
- mode
- tool_used
- generated_sql nullable
- result_summary
- created_at

## 9.3 Indexing priorities

Add indexes for:
- sessions(started_at)
- sessions(status)
- sessions(game_id, started_at)
- sessions(device_id, started_at)
- sessions(user_id, started_at)
- daily_game_stats(date, game_id)
- daily_system_stats(date, system_name)
- devices(hostname)
- session_events(dedupe_key)

---

# 10. API Design Plan

## 10.1 Core API groups

### Health
- `GET /api/health`
- `GET /api/version`

### Dashboard
- `GET /api/dashboard/home`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/kiosk`

### Sessions
- `POST /api/session/start`
- `POST /api/session/end`
- `POST /api/session/heartbeat`
- `GET /api/sessions/active`
- `GET /api/sessions/recent`
- `GET /api/sessions`
- `GET /api/sessions/{id}`

### Games
- `GET /api/games`
- `GET /api/games/top`
- `GET /api/games/{id}`
- `GET /api/games/{id}/sessions`

### Systems
- `GET /api/systems`
- `GET /api/systems/top`
- `GET /api/systems/{system_name}`

### Devices
- `GET /api/devices`
- `GET /api/devices/{hostname}`
- `POST /api/devices/heartbeat`

### AI
- `POST /api/ai/chat`
- `POST /api/ai/query`
- `GET /api/ai/history`
- `GET /api/ai/conversations/{id}`

### Controller
- `GET /api/controller/profile`
- `POST /api/controller/profile`
- `PUT /api/controller/profile/{id}`
- `GET /api/controller/layouts`

### Achievements
- `GET /api/achievements`
- `GET /api/achievements/user/{user_id}`

### Admin
- `GET /api/admin/diagnostics`
- `GET /api/admin/logs`
- `GET /api/admin/queue-status`

---

# 11. AI Migration and Upgrade Plan

## 11.1 Goal

Keep the AI features, but make them genuinely useful for PiStation by allowing the assistant to answer questions about:

- most played games
- current activity
- total playtime
- favourite systems
- streaks
- long sessions
- trends over time
- recommendations based on behaviour
- player comparisons
- device activity
- anomalies and insights

## 11.2 Critical security rule

The AI should **not** get unrestricted direct database access.

Instead, AI should access data through a safe backend orchestration layer.

## 11.3 AI architecture

### Flow
1. User sends a message from the chat UI
2. FastAPI receives it at `/api/ai/chat`
3. Backend classifies intent
4. Backend decides whether tools are needed
5. Allowed tools query analytics data
6. AI synthesises the result into a response
7. Conversation is saved
8. Optional voice output is generated

## 11.4 AI modes

### Mode A — General assistant
For help, explanation, troubleshooting, navigation guidance, and non-data questions.

### Mode B — Analytics assistant
For questions like:
- “What have I played most this week?”
- “Which system do I spend the most time on?”
- “What are my longest sessions?”

### Mode C — Recommendation assistant
For questions like:
- “What should I play next?”
- “Recommend something based on my short-session habits”
- “Which neglected system should I revisit?”

### Mode D — Voice assistant
For:
- speech input via Whisper
- answer generation via Ollama/tools
- voice output via Kokoro

## 11.5 Safe tool design

### Tool category 1 — fixed analytics functions
Examples:
- get_top_games(range)
- get_top_systems(range)
- get_total_playtime(user, range)
- get_active_sessions()
- get_longest_sessions(range)

These should use service functions, not freeform SQL.

### Tool category 2 — controlled SQL generation
For more flexible questions:
- only use allowlisted views/tables
- read-only database account
- strict validation
- no DDL/DML
- no unsafe joins
- row limits
- timeout limits
- query logging

### Tool category 3 — summarisation tools
These turn results into:
- explanations
- trends
- concise natural language answers
- recommendations

## 11.6 AI service modules

Recommended backend modules:
- `ai_service.py`
- `ai_tools_service.py`
- `ai_sql_service.py`
- `ai_prompt_service.py`
- `ai_audit_service.py`

## 11.7 Suggested AI quick prompts in the UI

Add quick actions like:
- “What have I played the most this week?”
- “Which system do I use the most?”
- “What are my shortest and longest sessions?”
- “What’s trending right now?”
- “Recommend something based on my recent activity.”
- “Summarise this month’s play habits.”

## 11.8 Voice integration plan

### Input
- microphone input
- Whisper transcription

### Processing
- AI chat orchestration
- tools / analytics lookup
- Ollama reasoning / response generation

### Output
- Kokoro TTS
- optional subtitle panel
- optional voice toggle in settings

---

# 12. Controller Compatibility Plan

## 12.1 Goal

Support:
- controller-first navigation
- optional controller-as-cursor mode
- keyboard and mouse support
- mixed-input switching
- TV-friendly focus behaviour

## 12.2 Core principle

You need **two controller input modes**:

### Navigation mode
Controller moves focus between UI elements like a console interface.

### Cursor mode
Controller moves a virtual on-screen mouse pointer.

Both should exist, but **navigation mode should be the default**.

## 12.3 Why focus navigation should come first

Cursor-only controller UI is possible, but inferior for most dashboard experiences because it is:
- slower
- less predictable
- harder to use at distance
- more tiring on TV interfaces

So build:
1. focus navigation first
2. virtual cursor second

## 12.4 Navigation mode design

### Primary mapping
- D-pad / left stick → move focus
- A → activate
- B → back / close
- X → secondary action
- Y → quick action / shortcut
- LB / RB → previous/next tab
- LT / RT → previous/next section
- Start → open quick menu
- Select → open AI
- Right stick click → toggle cursor mode

### Requirements
- every interactive item must be focusable
- focus order must be intentional
- visible focus ring must be large and clear
- no hover-only interactions
- all primary actions must be controller reachable

## 12.5 Cursor mode design

### Example mapping
- left stick → move cursor
- right stick → scroll
- A → left click
- B → back or escape
- X → alternate click / secondary action
- LT / RT → speed modifier / horizontal scroll
- RS click → return to focus navigation mode

### Cursor settings
- deadzone
- acceleration
- smoothing
- sensitivity
- snapping
- auto-hide
- magnetic target assist

## 12.6 Mixed input support

The app should detect current active input mode:
- mouse movement → enter pointer mode
- D-pad / focus input → enter controller mode
- keyboard tab/arrows → enter keyboard mode

This allows:
- controller
- keyboard
- mouse
to all coexist without conflict.

## 12.7 Required frontend hooks/modules

- `useGamepadNavigation.ts`
- `useFocusGraph.ts`
- `useVirtualCursor.ts`
- `useInputMode.ts`
- `useControllerProfile.ts`

## 12.8 Focus graph plan

Each page should define:
- default focus element
- up/down/left/right relationships where needed
- escape behaviour
- section boundaries
- modal focus traps
- return-to-origin focus after closing overlays

## 12.9 Controller settings persistence

Store profiles in backend:
- user-specific
- device-specific
- default profile fallback

Persist:
- button remaps
- cursor sensitivity
- deadzones
- navigation behaviour
- preferred mode

## 12.10 Accessibility note

All functionality must remain accessible through:
- keyboard
- mouse
- controller

No important feature should be locked behind controller-only interaction.

---

# 13. Kiosk / Pi Display Plan

## 13.1 Goal

Run the full app on the laptop, while the Pi only displays a fullscreen browser route.

## 13.2 Required conditions

To make this viable:
- browser launches reliably on Pi
- kiosk route exists
- fullscreen behaviour is fixed
- controller navigation works well on TV
- page density is reduced for Pi display

## 13.3 Kiosk route design

Add a dedicated route:
- `/dashboard/kiosk`
- or `/kiosk`

This route should:
- use full viewport width/height
- remove dense admin chrome
- enlarge typography
- reduce animation
- prioritise controller navigation
- show key dashboard content only

## 13.4 Kiosk shell recommendations

The kiosk route should include:
- top summary cards
- current session
- recent sessions
- top games
- active devices
- AI quick access
- footer/status

It should not prioritise:
- dense tables
- tiny settings panels
- complex nested admin navigation

---

# 14. Achievements Migration Plan

## 14.1 Keep the concept, change the source

The achievements system is worth preserving, but it should become backend-driven rather than local-emulator-driven.

## 14.2 Achievement ideas for PiStation

- First Session
- First Hour Played
- Ten Hours Played
- Marathon Session
- Five Systems Explored
- Weekend Warrior
- Night Owl
- Three-Day Streak
- Seven-Day Streak
- AI First Question
- Stats Explorer
- Retro Explorer
- Favourite Finder
- Controller Master
- Device Loyalist

## 14.3 Trigger model

Achievements should be unlocked on:
- session end
- milestone crossing
- AI interactions
- device usage milestones
- controller usage milestones
- streak calculations

---

# 15. Authentication and Multi-User Strategy

## 15.1 MVP
Start simple:
- default single-user mode
- optional manual user tagging
- device association

## 15.2 Future auth
Add later:
- login/registration
- username or email login
- per-user dashboard
- per-user controller profiles
- per-user AI chat history
- per-user achievements
- per-user favourites and recommendations

Do not make auth the first migration task unless absolutely necessary.

---

# 16. Performance Strategy

## 16.1 Laptop-side performance
The laptop can handle:
- React frontend
- FastAPI backend
- MySQL
- AI orchestration
- live analytics
- voice stack

Optimisations:
- route code-splitting
- cached aggregates
- SSE or light polling
- memoised components
- precomputed daily stats tables

## 16.2 Pi-side performance
Since the Pi is a thin client, optimise for:
- light kiosk route
- fewer heavy charts
- reduced motion
- simple card-based layout
- minimal unnecessary re-renders
- fullscreen browser stability

Avoid:
- giant animation libraries in kiosk mode
- complex visual effects
- expensive charts on every refresh

---

# 17. Migration Milestones

## Milestone 1 — Stabilise and strip emulator logic
- create migration branch
- remove or stub emulator-only routes
- ensure app still boots
- document removed modules

## Milestone 2 — Build typed API layer
- add API client
- add DTOs
- connect Home and Dashboard to FastAPI
- add error/loading states

## Milestone 3 — Platform backend
- expand FastAPI endpoints
- model devices, games, sessions, systems
- add heartbeats
- add aggregates

## Milestone 4 — Core product pages
- Dashboard
- Sessions
- Games
- Systems
- Devices
- Settings

## Milestone 5 — AI integration
- restore chat UI
- add safe backend tools
- add DB-grounded analytics mode
- add suggested prompts

## Milestone 6 — Controller-first UX
- gamepad detection
- focus graph
- remapping
- focus rings
- virtual cursor
- mixed input mode

## Milestone 7 — Kiosk polish
- fullscreen route
- large-text TV layout
- reduced motion
- EmulationStation launch compatibility

## Milestone 8 — Achievements and polish
- backend-driven achievements
- theme refinement
- admin diagnostics
- device health
- richer insights

---

# 18. Risk Register

## Risk 1 — Preserving too much emulator logic
### Problem
Old emulator assumptions may keep breaking the new app.
### Mitigation
Remove emulator logic early and clearly.

## Risk 2 — Frontend/backend mismatch
### Problem
React pages expect shapes that API does not yet supply.
### Mitigation
Define typed contracts early and version DTOs.

## Risk 3 — AI hallucination on data questions
### Problem
AI may invent answers if not grounded.
### Mitigation
Use tool-first analytics and safe SQL with audit logging.

## Risk 4 — Controller UX feeling poor
### Problem
Controller navigation may feel bolted-on.
### Mitigation
Design focus navigation intentionally, not as an afterthought.

## Risk 5 — Pi browser performance or fullscreen instability
### Problem
Display route may feel unreliable on Pi.
### Mitigation
Use laptop-hosted app, dedicated kiosk route, lightweight layout, and stable browser launch flow.

## Risk 6 — Too much scope at once
### Problem
Trying to do AI, controller, auth, achievements, and analytics simultaneously may stall progress.
### Mitigation
Build in milestones and protect a usable MVP first.

---

# 19. Recommended Build Order

If this were implemented as efficiently as possible, the recommended order would be:

1. preserve and stabilise the React shell
2. remove browser-emulator runtime logic
3. create typed API modules in the frontend
4. expand FastAPI into a full domain API
5. redesign data models around MySQL
6. convert Dashboard, Sessions, Games, Systems, Devices
7. restore AI with safe database-aware tooling
8. design controller-first navigation
9. add optional virtual cursor mode
10. add kiosk route and Pi-friendly layout
11. add achievements and advanced polish
12. add multi-user support later

---

# 20. Non-Negotiable Rules

## Rule 1
Frontend never talks directly to MySQL.

## Rule 2
AI never gets unrestricted raw database access.

## Rule 3
Controller navigation is designed intentionally from the start.

## Rule 4
Pi is treated as a display client, not a compute host.

## Rule 5
Backend becomes the source of truth for analytics and achievements.

## Rule 6
Every important action must remain usable by controller, keyboard, and mouse.

---

# 21. Final Recommendation

For this project, the best overall strategy is:

- keep the **React shell and UI system**
- remove the **browser-emulation product logic**
- connect everything to your **FastAPI/MySQL backend**
- keep and enhance the **AI**
- give the AI **safe, tool-based access to analytics data**
- build **controller-first navigation**
- add an optional **virtual cursor**
- run everything heavy on the **laptop**
- use the Pi only as the **fullscreen display/browser client**

This gives you:
- the polished UI you want
- the database-backed analytics you need
- the AI features you want to preserve
- the controller compatibility you want to showcase
- a stronger and more defensible final year project architecture

---

# 22. Suggested Immediate Next Deliverables

After this migration document, the next most useful implementation documents would be:

1. `TASKS.md` — a milestone-based implementation checklist
2. `ARCHITECTURE.md` — system architecture and data flow
3. `API_CONTRACTS.md` — request/response models for frontend/backend
4. `AI_TOOLS_SPEC.md` — safe analytics tool design for AI
5. `CONTROLLER_UX_SPEC.md` — controller navigation and cursor behaviour
6. `DB_SCHEMA.sql` or migration files — full schema implementation
