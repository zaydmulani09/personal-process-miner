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
├── sidecar/
│   ├── __init__.py
│   ├── capture.py         # keyboard/mouse/window capture module
│   ├── db.py              # SQLite schema + insert/query helpers
│   ├── main.py            # stdin/stdout JSON IPC daemon
│   ├── requirements.txt
│   ├── sidecar.log        # runtime log (gitignored)
│   ├── test_capture.py    # capture smoke-test
│   └── test_ipc.py        # IPC smoke-test
├── src/
│   ├── App.tsx
│   ├── App.css
│   ├── main.tsx
│   ├── vite-env.d.ts
│   └── pages/
│       └── Dashboard.tsx
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs         # sidecar spawn + shutdown logic
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
| P4 | | pending |
| P5 | | pending |
| P6 | | pending |
| P7 | | pending |
| P8 | | pending |
| P9 | | pending |
| P10 | | pending |
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

2 (sidecar/test_ipc.py — IPC smoke-test with 7 assertions; sidecar/test_capture.py — capture + DB smoke-test)

## Known Issues

None.

## Deviations

- **Rust toolchain**: Default system toolchain was `x86_64-pc-windows-gnu` (missing `dlltool.exe`). Switched to `x86_64-pc-windows-msvc` via `rustup override`. VS Build Tools 2022 installed via winget.
- **MSVC linker PATH conflict**: Git's `link.exe` shadowed MSVC's. Fixed via `.cargo/config.toml` with explicit linker path.
- **Build verification**: Used `npm run tauri build -- --no-bundle` (release build) instead of `tauri dev` to confirm compilation. Dev mode requires opening a window interactively.
- **externalBin omitted**: Tauri's `bundle.externalBin` requires the compiled binary (e.g., `main-x86_64-pc-windows-msvc.exe`) to exist at build time. Since Python is not yet compiled via PyInstaller, `externalBin` is deferred to a later prompt. Rust spawns `py sidecar/main.py` directly via `tauri-plugin-shell` instead of `Command::new_sidecar`.
- **Python command**: System `python` alias points to Windows Store stub. Using `py` launcher (Python 3.11.9 via Python Launcher for Windows).
- **data/ gitignored**: `data/events.db` is a runtime artifact, not a build artifact. Directory is created automatically by `db.py` on first use.
