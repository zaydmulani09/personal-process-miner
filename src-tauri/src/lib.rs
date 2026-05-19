use std::sync::Mutex;
use tauri::{Manager, WindowEvent};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

struct SidecarState(Mutex<Option<CommandChild>>);

// Path to the Python script, resolved at compile time relative to src-tauri/.
const SIDECAR_SCRIPT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../sidecar/main.py");

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(SidecarState(Mutex::new(None)))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let (mut rx, mut child) = app
                .shell()
                .command("py")
                .args([SIDECAR_SCRIPT])
                .spawn()
                .expect("failed to spawn python sidecar");

            // Send initial ping to confirm channel is live.
            child
                .write(b"{\"type\": \"ping\"}\n")
                .expect("failed to write ping to sidecar");

            // Read responses asynchronously.
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log::info!("sidecar stdout: {}", text.trim());
                        }
                        CommandEvent::Stderr(line) => {
                            let text = String::from_utf8_lossy(&line);
                            log::warn!("sidecar stderr: {}", text.trim());
                        }
                        CommandEvent::Terminated(payload) => {
                            log::info!("sidecar terminated: code={:?}", payload.code);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            *app.state::<SidecarState>().0.lock().unwrap() = Some(child);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<SidecarState>();
                let mut guard = state.0.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.write(b"{\"type\": \"shutdown\"}\n");
                    std::thread::sleep(std::time::Duration::from_millis(300));
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
