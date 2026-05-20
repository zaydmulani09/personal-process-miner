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
│   ├── requirements.txt
│   ├── seed.py            # realistic sample data seeder
│   ├── fingerprinter.py   # sliding-window sequence detector + fuzzy dedup
│   ├── segmenter.py       # session segmentation engine
│   ├── sidecar.log        # runtime log (gitignored)
│   ├── test_capture.py    # capture smoke-test
│   ├── test_db.py         # DB layer test (in-memory)
│   ├── test_fingerprinter.py  # fingerprinter unit tests (7 cases)
│   ├── test_ipc.py        # IPC smoke-test
│   ├── test_ranker.py     # ranker unit tests (5 cases)
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
│   │   ├── WorkflowCard.tsx       # card with badge, steps pills, stats, name/delete/record buttons
│   │   ├── LabelWorkflowModal.tsx # modal with editable steps, name input, save/cancel
│   │   ├── ActivityHeatmap.tsx    # 12-week session activity grid (plain CSS grid, hover tooltip)
│   │   ├── StatsBar.tsx           # 4-metric responsive stats cards
│   │   ├── CaptureControls.tsx    # start/stop capture toggle + analyze-now sequence
│   │   └── MacroRecorder.tsx      # recording modal: start/stop/save/discard + live event count
│   └── pages/
│       └── Dashboard.tsx  # full dashboard: summary cards, workflow list, modal management
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
| P11 | | pending |
| P12 | | pending |
| P13 | | pending |
| P14 | | pending |
| P15 | | pending |
| P16 | | pending |
| P17 | | pending |
| P18 | | pending |
| P19 | | pending |
| P20 | | pending |
| P21 | | pending |
| P22 | | pending |

## Test Count

7 scripts:
- `sidecar/test_ipc.py` — IPC smoke-test (10 assertions)
- `sidecar/test_capture.py` — capture + DB file smoke-test
- `sidecar/test_db.py` — DB layer test on in-memory SQLite (all tables, all helpers)
- `sidecar/test_segmenter.py` — segmenter unit tests (5 cases: idle gap, midnight, dominant app, empty/single, live DB)
- `sidecar/test_fingerprinter.py` — fingerprinter unit tests (7 cases: extract, windows, stability, edit distance, find_patterns freq, min-freq filter, live DB)
- `sidecar/test_ranker.py` — ranker unit tests (5 cases: score_workflow, ordering, human formatting, live DB summary, empty list)
- `sidecar/test_ipc.py` now includes label_workflow and delete_workflow IPC tests (14 total assertions)
- `sidecar/test_macro_recorder.py` — macro recorder unit tests (5 cases: start/stop, double-start guard, script generation, empty script, save_macro file+DB)
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
- **Navigation: left sidebar**: Chose 200px dark left sidebar (`#1e293b`) over top bar. Desktop-app layout with sidebar scales better as more pages are added in later prompts.
- **recharts installed but unused in P9**: `recharts` installed as specified; heatmap uses plain CSS grid per spec. Will be used in a later prompt.
- **App.css imported in main.tsx**: Added `import "./App.css"` to `src/main.tsx` — it was missing from the scaffold, which would have prevented CSS variables and skeleton animation from loading.
- **`--color-background-secondary` and `--color-heatmap-empty`**: CSS vars defined in `:root` with dark-mode overrides in `@media (prefers-color-scheme: dark)`.
