# Personal Process Miner — Project Context

## What It Is

Privacy-first, local-only desktop app that watches repetitive computer workflows and turns them into one-click automations. All data stays on device. No cloud, no telemetry.

## Tech Stack

| Layer | Tech | Version |
|-------|------|---------|
| Desktop shell | Tauri | v2.11.2 |
| Frontend | React | 18 |
| Language | TypeScript | 5 |
| Bundler | Vite | 6 |
| Rust | rustc | 1.95.0 (MSVC toolchain) |
| IPC daemon | Python | 3.11.9 (via `py` launcher) |
| Event capture | pynput | 1.8.2 |
| Window polling | pygetwindow | 0.0.9 |
| Storage | SQLite (stdlib sqlite3) | — |
| DB (frontend, planned) | better-sqlite3 | later |

## File Tree

```
personal-process-miner/
├── .cargo/
│   └── config.toml        # MSVC linker path override
├── data/                  # runtime only — gitignored
│   └── events.db
├── data/
│   └── macros/
│       └── .gitkeep       # keeps directory tracked; *.py files are gitignored
├── sidecar/
│   ├── __init__.py
│   ├── capture.py         # keyboard/mouse/window capture module
│   ├── db.py              # migrations runner + all schema helpers
│   ├── main.py            # stdin/stdout JSON IPC daemon
│   ├── macro_recorder.py  # pynput macro recorder + pyautogui script generator
│   ├── requirements.txt   # pynput, pygetwindow, pyautogui, playwright
│   ├── scheduler.py       # OS-level scheduling (Windows schtasks / Unix crontab)
│   ├── seed.py            # realistic sample data seeder
│   ├── fingerprinter.py   # sliding-window sequence detector + fuzzy dedup
│   ├── llm_explainer.py   # optional LLM script explainer (Ollama/Claude), opt-in via env vars
│   ├── playwright_gen.py  # rule-based playwright script generator from browser events
│   ├── segmenter.py       # session segmentation engine
│   ├── sidecar.log        # runtime log (gitignored)
│   ├── test_capture.py    # capture smoke-test
│   ├── test_db.py         # DB layer test (in-memory)
│   ├── test_fingerprinter.py  # fingerprinter unit tests (7 cases)
│   ├── test_ipc.py        # IPC smoke-test
│   ├── test_llm_explainer.py   # LLM explainer unit tests (5 cases, all offline)
│   ├── test_playwright_gen.py  # playwright generator unit tests (6 cases)
│   ├── test_ranker.py     # ranker unit tests (5 cases)
│   ├── test_scheduler.py  # scheduler unit tests (5 tests, 12 assertions)
│   ├── test_segmenter.py  # segmenter unit tests
│   └── ranker.py          # workflow scoring, time-wasted stats, summary aggregation
├── src/
│   ├── App.tsx
│   ├── App.css
│   ├── main.tsx
│   ├── vite-env.d.ts
│   ├── lib/
│   │   ├── sidecar.ts     # sendToSidecar IPC utility + SidecarError
│   │   └── types.ts       # Workflow, Session, SummaryStats, Automation types
│   ├── components/
│   │   ├── WorkflowCard.tsx       # card with badge, steps pills, stats, name/delete/record/script/improve buttons
│   │   ├── LabelWorkflowModal.tsx # modal with editable steps, name input, save/cancel
│   │   ├── ActivityHeatmap.tsx    # 12-week session activity grid (plain CSS grid, hover tooltip)
│   │   ├── StatsBar.tsx           # 4-metric responsive stats cards
│   │   ├── CaptureControls.tsx    # start/stop capture toggle + analyze-now sequence
│   │   ├── AutomationCard.tsx     # card with inline rename, type badge, stats, script preview, run/schedule/delete
│   │   ├── ImproveScriptModal.tsx # LLM improve modal: setup instructions or AI improvement flow
│   │   ├── MacroRecorder.tsx      # recording modal: start/stop/save/discard + live event count
│   │   └── ScriptPreviewModal.tsx # playwright script preview: load, edit name, save/close
│   └── pages/
│       ├── Automations.tsx  # automation library: stats bar, filter toggles, AutomationCard list
│       ├── Dashboard.tsx    # full dashboard: summary cards, workflow list, modal management
│       ├── Onboarding.tsx   # first-run wizard: welcome, permission, privacy, demo, done (steps 0-4)
│       └── Settings.tsx     # privacy controls: capture toggles, app blocklist, retention, purge
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs         # sidecar spawn + send_to_sidecar command (request/response IPC)
│   │   └── main.rs
│   ├── capabilities/
│   │   └── default.json
│   ├── icons/
│   ├── build.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── public/
│   ├── tauri.svg
│   └── vite.svg
├── CONTEXT.md
├── PROMPT_ENGINEER_HANDOFF.md
├── .gitignore
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Prompt Status

| Prompt | Description | Status |
|--------|-------------|--------|
| P1 | Tauri + React scaffold & GitHub repo init | complete |
| P2 | Python sidecar IPC daemon | complete |
| P3 | Event capture module (keyboard/mouse/window + SQLite) | complete |
| P4 | SQLite schema & migrations + seed data | complete |
| P5 | Session segmenter (idle gap, midnight boundary, max-length) | complete |
| P6 | Sequence fingerprinter (sliding window + edit-distance fuzzy dedup) | complete |
| P7 | Pattern ranker & stats (scoring, time-wasted, summary aggregation) | complete |
| P8 | Manual labeling flow (UI + backend label/delete, Tauri IPC bridge, dashboard) | complete |
| P9 | Pattern dashboard UI (heatmap, stats bar, capture controls, nav shell) | complete |
| P10 | Macro recorder (start/stop/save, script generation, UI recording flow) | complete |
| P11 | Playwright script generator (browser event detection, preview modal, save automation) | complete |
| P12 | LLM script explainer (Ollama/Claude backends, improve automation, opt-in via env vars) | complete |
| P13 | Automation library UI (run, rename, delete, stats, Automations page + nav) | complete |
| P14 | One-click run hardening, safety checks, OS-level task scheduling | complete |
| P15 | Privacy controls: settings page, app blocklist, data retention, purge | complete |
| P16 | First-run onboarding wizard: permission check, demo recording, privacy explainer | complete |
| P17 | | pending |
| P18 | | pending |
| P19 | | pending |
| P20 | | pending |
| P21 | | pending |
| P22 | | pending |

## Test Count

8 scripts (updated test_db.py + test_ipc.py with privacy tests):
- `sidecar/test_ipc.py` — IPC smoke-test (27 assertions: prev 20 + get_onboarding_state, set_onboarding_step, check_accessibility, set_onboarding_complete)
- `sidecar/test_capture.py` — capture + DB file smoke-test
- `sidecar/test_db.py` — DB layer test on in-memory SQLite (all tables, all helpers; +5 privacy: migration 5, get/set_setting, get_all_settings, purge_all_data, purge_old_events zero-retention)
- `sidecar/test_segmenter.py` — segmenter unit tests (5 cases: idle gap, midnight, dominant app, empty/single, live DB)
- `sidecar/test_fingerprinter.py` — fingerprinter unit tests (7 cases: extract, windows, stability, edit distance, find_patterns freq, min-freq filter, live DB)
- `sidecar/test_ranker.py` — ranker unit tests (5 cases: score_workflow, ordering, human formatting, live DB summary, empty list)
- `sidecar/test_macro_recorder.py` — macro recorder unit tests (5 cases: start/stop, double-start guard, script generation, empty script, save_macro file+DB)
- `sidecar/test_playwright_gen.py` — playwright generator unit tests (6 cases: is_browser_event, extract_url_from_title, classify_event, group_keystrokes, no-browser-events script, full script structure)
- `sidecar/test_llm_explainer.py` — LLM explainer unit tests (5 cases: backend empty, invalid Ollama URL, disabled explain_script, fence stripping, get/update automation by id — all offline)
- `sidecar/test_scheduler.py` — scheduler unit tests (5 tests, 12 assertions: get_platform, schedule/unschedule Windows, list_scheduled, is_script_safe)
- `sidecar/seed.py` — not a test, but verifies seeder runs clean (59 rows)

## Known Issues

None.

## Deviations

- **Rust toolchain**: Default system toolchain was `x86_64-pc-windows-gnu` (missing `dlltool.exe`). Switched to `x86_64-pc-windows-msvc` via `rustup override`. VS Build Tools 2022 installed via winget.
- **MSVC linker PATH conflict**: Git's `link.exe` shadowed MSVC's. Fixed via `.cargo/config.toml` with explicit linker path.
- **Build verification**: Used `npm run tauri build -- --no-bundle` (release build) instead of `tauri dev` to confirm compilation. Dev mode requires opening a window interactively.
- **externalBin omitted**: Tauri's `bundle.externalBin` requires the compiled binary (e.g., `main-x86_64-pc-windows-msvc.exe`) to exist at build time. Since Python is not yet compiled via PyInstaller, `externalBin` is deferred to a later prompt. Rust spawns `py sidecar/main.py` directly via `tauri-plugin-shell` instead of `Command::new_sidecar`.
- **Python command**: System `python` alias points to Windows Store stub. Using `py` launcher (Python 3.11.9 via Python Launcher for Windows).
- **data/ gitignored**: `data/events.db` is a runtime artifact. Directory is created automatically by `db.py` on first use.
- **update_session allowlist**: `update_session` filters keys against a hardcoded column allowlist to prevent accidental SQL injection from internal callers. Only `started_at`, `ended_at`, `event_count`, `dominant_app` are accepted.
- **Tauri IPC bridge**: replaced the fire-and-forget stdout reader with `tokio::sync::mpsc` channel forwarding. `send_to_sidecar` holds a `tokio::sync::Mutex` across write+recv to serialize request/response. `try_lock()` used in the sync window-close handler. `tokio = { version = "1", features = ["sync"] }` added as an explicit Cargo dependency.
- **seed required before IPC tests**: `test_ipc.py` label/delete tests require at least one workflow in `data/events.db`. Run `py sidecar/seed.py` before running the IPC test suite.
- **data/ gitignore replaced**: Changed from ignoring all of `data/` to ignoring only `data/events.db` and `data/macros/*.py`. This allows `data/macros/.gitkeep` to be tracked.
- **_state exposed for testing**: `macro_recorder._state["buffer"]` is accessed directly in `test_macro_recorder.py` to inject synthetic events for Test 5. No separate test helper added.
- **MacroRecorder modal managed in WorkflowCard**: The `MacroRecorder` modal state (`showRecorder`) is local to `WorkflowCard`, keeping the component self-contained rather than lifting state to Dashboard.
- **`classify_event` accepts multi-char details**: After `group_keystrokes` merges consecutive keystrokes into a single event with a multi-char `detail` string, `classify_event` must still return "type" for it. Changed the check from `len(inner) == 1` to `inner and not inner.startswith("Key.")` — this correctly classifies both single and merged char events as "type" while still rejecting `Key.space` etc.
- **Rust borrow lifetime fix in shutdown handler**: The `on_window_event` closure had a borrow issue where the `MutexGuard` (from `try_lock`) could outlive the `state` binding. Fixed by wrapping the `try_lock` in a nested block `{}` that drops the guard before `state` goes out of scope.
- **LLM feature is opt-in via env vars, disabled by default**: `PPM_LLM_BACKEND` defaults to `""` (disabled). Set to `"ollama"` or `"claude"` to enable. No backend = app works exactly as before. Ollama availability check uses a 1s timeout (reduced from 2s to keep the `is_llm_available()` call fast on Windows).
- **`✨ Improve` button gated on automation existence**: `Dashboard.tsx` fetches all automations and passes the matching one (by `workflow_id`) as an optional prop to `WorkflowCard`. The button only renders when an automation prop is present, avoiding a schema change to the `Workflow` type.
- **`run_automation` uses temp file on Windows**: `subprocess.run` needs the script written to a real file (not stdin pipe) because pyautogui and playwright scripts use `if __name__ == "__main__"` guards. `tempfile.NamedTemporaryFile(delete=False)` is used because Windows cannot open a NamedTemporaryFile from a second handle while it's still open; the file is deleted in a `finally` block.
- **`delete_automation` reconstructs script path from name slug**: The `automations` table has no `script_path` column. The file path is reconstructed from the automation name using the same slug logic as `save_macro` / `save_playwright_script`. If the file was renamed or moved, deletion silently succeeds (row deleted, file skip).
- **`estimated_time_saved_seconds` = total_runs × 120**: A fixed 2-minute-per-run estimate. No actual timing is tracked; this is a motivational heuristic, not a measurement.
- **Automations page nav uses local `page` state in `App.tsx`**: Simple `useState<"dashboard" | "automations">` swap — no router needed at this scale.
- **`is_script_safe` exported from `main.py`**: Extracted as a module-level function (not a nested helper) so `test_scheduler.py` can import it directly for Test 5.
- **`schedule_automation` writes a persistent `.py` to `data/macros/`**: The IPC handler writes `{name_slug}_sched.py` before calling `scheduler.schedule_automation` so the OS scheduler has a durable script path to invoke. The temp-file approach used for interactive runs is not suitable for scheduled tasks.
- **`scheduler.py` uses `schtasks` on Windows**: Windows Task Scheduler is invoked via `schtasks /create` with `/f` (force overwrite). Weekly schedules pass `/d {MON..SUN}`. The task name prefix `PPM_` separates app-managed tasks from system ones.
- **`onboarding_complete` / `onboarding_step` seeded in `privacy_settings`**: No new migration; uses `INSERT OR IGNORE` in the existing migration 5 seed block. `_DEFAULT_SETTINGS` dict extended.
- **Step 1 (permission check) auto-passes on Windows/Linux**: `check_accessibility` IPC returns `granted: true` immediately. Frontend auto-advances after 800ms showing "✓ Ready". macOS path tests pynput listener creation.
- **Allowlist has no UI (known debt)**: `allowlist_apps` is wired in `capture.py` but Settings page only exposes blocklist. Documented for P17+.
- **`open` → `openUrl` in plugin-opener**: Tauri v2 `@tauri-apps/plugin-opener` exports `openUrl`, not `open`. Build error fixed.
- **Onboarding wizard renders full-screen**: No sidebar/nav. `App.tsx` renders `<Onboarding>` instead of the entire shell layout when `onboarding_complete == false`. Loading spinner prevents flash of wrong content.
- **Migration 5 adds `privacy_settings` table**: 5 default settings seeded via `INSERT OR IGNORE` in `run_migrations` after all migrations applied. Safe to re-run.
- **Privacy settings loaded once at `start_capture()`**: `_blocklist`, `_allowlist`, `_capture_keystrokes`, `_capture_mouse_moves` module-level vars updated on each `start_capture()` call. No mid-session reload.
- **`capture_mouse_moves` setting present but no mouse-move events were stored before P15**: pynput `on_move` callback was absent in earlier code; setting now controls whether callback is attached. `on_move=None` passed when disabled.
- **`purge_all_data` is destructive and irreversible**: Settings page requires typing `"DELETE"` before enabling the button; on success, navigates to Dashboard after 1.5s.
- **`scheduled` / `schedule_info` fields are client-side only**: The `automations` DB table has no scheduling columns. `AutomationCard` tracks `isScheduled` / `scheduleInfo` in local React state after a successful `schedule_automation` response. A page refresh will show the badge as unscheduled until the backend returns schedule state (deferred to a later prompt with a `get_scheduled_info` IPC call).
- **Navigation: left sidebar**: Chose 200px dark left sidebar (`#1e293b`) over top bar. Desktop-app layout with sidebar scales better as more pages are added in later prompts.
- **recharts installed but unused in P9**: `recharts` installed as specified; heatmap uses plain CSS grid per spec. Will be used in a later prompt.
- **App.css imported in main.tsx**: Added `import "./App.css"` to `src/main.tsx` — it was missing from the scaffold, which would have prevented CSS variables and skeleton animation from loading.
- **`--color-background-secondary` and `--color-heatmap-empty`**: CSS vars defined in `:root` with dark-mode overrides in `@media (prefers-color-scheme: dark)`.
