# Personal Process Miner — Project Context

## What It Is

Privacy-first, local-only desktop app that watches repetitive computer workflows and turns them into one-click automations. All data stays on device. No cloud, no telemetry.

## Tech Stack

| Layer | Tech | Version |
|-------|------|---------|
| Desktop shell | Tauri | v2 |
| Frontend | React | 18 |
| Language | TypeScript | 5 |
| Bundler | Vite | 6 |
| Backend | Rust (Tauri core) | 1.95 |
| DB (planned) | SQLite via better-sqlite3 | later |
| Automation sidecar (planned) | Python | later |

## File Tree

```
personal-process-miner/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   └── pages/
│       └── Dashboard.tsx
├── src-tauri/
│   ├── src/
│   │   └── main.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── CONTEXT.md
├── PROMPT_ENGINEER_HANDOFF.md
├── .gitignore
└── package.json
```

## Prompt Status

| Prompt | Description | Status |
|--------|-------------|--------|
| P1 | Tauri + React scaffold & GitHub repo init | in progress |
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

None.
