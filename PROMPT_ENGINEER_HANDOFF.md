# Prompt Engineer Handoff — Personal Process Miner

## What the Project Is

Personal Process Miner is a privacy-first, local-only desktop app built with Tauri v2 + React + Python. It watches which apps a user switches between, detects repeated workflow sequences using sliding-window fingerprinting with edit-distance deduplication, and generates one-click PyAutoGUI macros or Playwright browser scripts. All data stays on device. No cloud, no telemetry. The project is fully built through P18 and is released as v0.1.0.

---

## Tech Stack

| Layer | Tech | Version |
|-------|------|---------|
| Desktop shell | Tauri | v2.11.2 |
| Frontend | React | 18 |
| Language | TypeScript | 5 |
| Bundler | Vite | 6 |
| Rust | rustc | 1.95.0 (MSVC toolchain) |
| IPC daemon | Python | 3.11.9 (via `py` launcher on Windows) |
| Event capture | pynput | 1.8.2 |
| Window polling | pygetwindow | 0.0.9 |
| Automation | pyautogui | 0.9.54 |
| Browser automation | playwright | 1.60.0 |
| Storage | SQLite (stdlib sqlite3) | — |
| Frontend router | local `useState` (no react-router) | — |

---

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
| P17 | Shareable insights card with weekly stats and top workflows | complete |
| P18 | GitHub Actions CI + README + Release (v0.1.0) | complete |

---

## File Tree

```
personal-process-miner/
├── .cargo/
│   └── config.toml            # MSVC linker path override
├── .github/
│   └── workflows/
│       ├── ci.yml             # push/PR to master → 5 headless-safe test scripts
│       └── release.yml        # v* tag → Windows + macOS build + GitHub Release
├── data/                      # runtime only — gitignored
│   ├── events.db
│   └── macros/                # .py scripts gitignored; .gitkeep tracked
├── sidecar/
│   ├── __init__.py
│   ├── capture.py             # keyboard/mouse/window capture; privacy filters at start_capture()
│   ├── db.py                  # migrations 1-5, all schema helpers, privacy settings, purge fns
│   ├── fingerprinter.py       # sliding-window sequence detector + fuzzy dedup
│   ├── llm_explainer.py       # optional Ollama/Claude script explainer + improver
│   ├── macro_recorder.py      # pyautogui macro recorder
│   ├── main.py                # stdin/stdout JSON IPC daemon (all handlers)
│   ├── playwright_gen.py      # rule-based Playwright script generator
│   ├── ranker.py              # workflow scoring, time-wasted stats
│   ├── requirements.txt       # pynput, pygetwindow, pyautogui, playwright
│   ├── scheduler.py           # OS-level scheduling (Windows schtasks / Unix crontab)
│   ├── seed.py                # realistic sample data seeder (59 rows)
│   ├── segmenter.py           # session segmentation engine
│   ├── sidecar.log            # runtime log (gitignored)
│   ├── test_capture.py        # capture smoke-test (OS GUI required)
│   ├── test_db.py             # DB layer test on in-memory SQLite
│   ├── test_fingerprinter.py  # fingerprinter unit tests (7 cases)
│   ├── test_ipc.py            # IPC smoke-test (34 assertions; requires seed + running sidecar)
│   ├── test_llm_explainer.py  # LLM explainer unit tests (5 cases, all offline)
│   ├── test_macro_recorder.py # macro recorder unit tests (5 cases)
│   ├── test_playwright_gen.py # playwright gen unit tests (6 cases; OS GUI required)
│   ├── test_ranker.py         # ranker unit tests (5 cases)
│   ├── test_scheduler.py      # scheduler unit tests (5 tests, 12 assertions)
│   └── test_segmenter.py      # segmenter unit tests (5 cases)
├── src/
│   ├── App.css
│   ├── App.tsx                # root: onboarding gate + 4-item sidebar nav
│   ├── main.tsx
│   ├── vite-env.d.ts
│   ├── components/
│   │   ├── ActivityHeatmap.tsx
│   │   ├── AutomationCard.tsx     # run/schedule/delete + inline schedule panel
│   │   ├── CaptureControls.tsx
│   │   ├── ImproveScriptModal.tsx
│   │   ├── InsightsCard.tsx       # 600px dark screenshot card
│   │   ├── LabelWorkflowModal.tsx
│   │   ├── MacroRecorder.tsx
│   │   ├── ScriptPreviewModal.tsx
│   │   ├── StatsBar.tsx
│   │   └── WorkflowCard.tsx
│   ├── lib/
│   │   ├── sidecar.ts             # sendToSidecar IPC utility
│   │   └── types.ts               # Workflow, Session, SummaryStats, Automation
│   └── pages/
│       ├── Automations.tsx        # automation library with stats + filter
│       ├── Dashboard.tsx          # full dashboard
│       ├── Onboarding.tsx         # 5-step first-run wizard
│       ├── Settings.tsx           # privacy controls
│       └── ShareInsights.tsx      # insights card + share flow
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs                 # sidecar spawn + send_to_sidecar Tauri command
│   │   └── main.rs
│   ├── capabilities/
│   │   └── default.json
│   ├── icons/
│   ├── build.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── public/
├── .gitignore
├── CONTEXT.md
├── LICENSE
├── PROMPT_ENGINEER_HANDOFF.md
├── README.md
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

---

## Test Suites

### Runs on CI (headless-safe)
| File | Cases |
|------|-------|
| `test_db.py` | in-memory SQLite, all tables, privacy settings, purge |
| `test_segmenter.py` | 5 cases: idle gap, midnight, dominant app, empty/single, live DB |
| `test_fingerprinter.py` | 7 cases: extract, windows, stability, edit distance, freq, filter, live DB |
| `test_ranker.py` | 5 cases: score_workflow, ordering, human formatting, live DB, empty list |
| `test_llm_explainer.py` | 5 cases: all offline, no live LLM required |

### Local-only (require OS GUI / running sidecar)
| File | Reason |
|------|--------|
| `test_ipc.py` | spawns sidecar subprocess; requires `py sidecar/seed.py` first |
| `test_capture.py` | pynput needs display |
| `test_macro_recorder.py` | writes files to `data/macros/` |
| `test_playwright_gen.py` | imports pyautogui which probes display |
| `test_scheduler.py` | calls `schtasks` on Windows |

---

## Known Deviations from Original Spec

- **Rust toolchain**: Switched from `x86_64-pc-windows-gnu` to `x86_64-pc-windows-msvc`. VS Build Tools 2022 required.
- **MSVC linker PATH conflict**: Git's `link.exe` shadowed MSVC's. Fixed via `.cargo/config.toml`.
- **`externalBin` omitted**: PyInstaller compilation deferred. Rust spawns `py sidecar/main.py` via `tauri-plugin-shell` directly.
- **Python command**: `python` alias → Windows Store stub. Using `py` launcher throughout.
- **Tauri IPC bridge**: `tokio::sync::mpsc` channel serializes request/response. `try_lock()` in sync close handler.
- **`classify_event` accepts multi-char details**: `group_keystrokes` merges consecutive keystroke events; check is `not inner.startswith("Key.")` not `len(inner) == 1`.
- **LLM opt-in only**: `PPM_LLM_BACKEND` defaults to `""`. App fully functional without it.
- **`run_automation` uses temp file**: Windows can't open NamedTemporaryFile from a second handle while held open. `delete=False` + `finally` cleanup.
- **`is_script_safe` blocks `subprocess` pattern**: the safety check scans `script_body` string, not the sidecar's own imports.
- **Scheduler writes persistent `.py` to `data/macros/`**: `schtasks` needs a durable file path.
- **`scheduled`/`schedule_info` fields are client-side only**: no DB column; state lives in AutomationCard local state per session.
- **Privacy settings loaded once at `start_capture()`**: no mid-session reload.
- **Allowlist has no UI**: wired in `capture.py`, not exposed in Settings. Known debt.
- **`openUrl` not `open` in plugin-opener**: Tauri v2 `@tauri-apps/plugin-opener` exports `openUrl`. Build-time TS error caught this.
- **Onboarding race condition risk**: sidecar must be running before `get_onboarding_state` fires on mount. No retry/backoff in frontend; watch during live testing.
- **InsightsCard hardcoded colors**: no CSS vars; ensures screenshot looks correct in both OS light/dark modes.
- **No html2canvas**: "Copy as Image" shows OS screenshot tip instead. Tauri clipboard image API would require a custom Rust command.
- **GitHub URL hardcoded in InsightsCard**: `github.com/zaydmulani09/personal-process-miner`.
- **`recharts` installed but unused through P18**: planned for a future analytics prompt.
- **CI skips GUI-requiring tests**: `test_capture.py`, `test_ipc.py`, `test_macro_recorder.py`, `test_playwright_gen.py`, `test_scheduler.py` are excluded from CI.

---

## Known Issues / Technical Debt

1. **Allowlist UI missing**: `allowlist_apps` is stored in DB and respected by `capture.py` but the Settings page has no UI for it. Next prompt should add an "Only record these apps" section to Settings.

2. **Onboarding sidecar race condition**: `App.tsx` calls `get_onboarding_state` on mount. If the sidecar hasn't finished spawning, the request will fail and `catch` returns `onboardingDone = true` (fail-open). A retry with exponential backoff or a Tauri readiness event would make this robust.

3. **Scheduled task state not persisted to DB**: `AutomationCard` tracks `isScheduled` in local React state. After a page reload, the badge disappears. A `scheduled_tasks` DB table or `get_scheduled_info` IPC call would fix this.

4. **`tauri dev` requires interactive display**: CI uses `npm run tauri build -- --no-bundle` for compilation checks. Live dev mode can't run headless.

5. **`externalBin` deferred**: App ships by running `py sidecar/main.py` directly. For true bundled distribution, sidecar should be compiled via PyInstaller and declared in `bundle.externalBin`.

6. **`recharts` installed but unused**: imported in `package.json`, not used. Remove or use in a future analytics page.

---

## How to Start a New Session

Paste this at the start of a new Claude session:

```
Project: Personal Process Miner (Tauri v2 + React + Python sidecar)
Repo: https://github.com/zaydmulani09/personal-process-miner
Branch: master (all 18 prompts complete, v0.1.0 tagged)
Context file: CONTEXT.md (read this first)
Handoff: PROMPT_ENGINEER_HANDOFF.md

The project is complete through P18. All tests pass. v0.1.0 is tagged and released.
Read CONTEXT.md before touching anything. Check git status and the current branch.
```
