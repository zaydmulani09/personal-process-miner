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
| DB (planned) | SQLite via better-sqlite3 | later |
| Automation sidecar (planned) | Python | later |

## File Tree

```
personal-process-miner/
├── .cargo/
│   └── config.toml        # MSVC linker path override
├── src/
│   ├── App.tsx
│   ├── App.css
│   ├── main.tsx
│   ├── vite-env.d.ts
│   └── pages/
│       └── Dashboard.tsx
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs
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
| P2 | | pending |
| P3 | | pending |
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

0

## Known Issues

None.

## Deviations

- **Rust toolchain**: Default system toolchain was `x86_64-pc-windows-gnu` (missing `dlltool.exe`). Switched to `x86_64-pc-windows-msvc` via `rustup override`. VS Build Tools 2022 installed via winget.
- **MSVC linker PATH conflict**: Git's `link.exe` shadowed MSVC's. Fixed via `.cargo/config.toml` with explicit linker path.
- **Build verification**: Used `npm run tauri build -- --no-bundle` (release build) instead of `tauri dev` to confirm compilation. Dev mode requires opening a window interactively.
