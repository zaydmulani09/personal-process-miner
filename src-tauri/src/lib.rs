use tauri::{Manager, WindowEvent};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tokio::sync::{mpsc, Mutex};

struct SidecarInner {
    child: CommandChild,
    stdout_rx: mpsc::UnboundedReceiver<String>,
}

struct SidecarState(Mutex<Option<SidecarInner>>);

#[tauri::command]
async fn send_to_sidecar(
    message: String,
    state: tauri::State<'_, SidecarState>,
) -> Result<String, String> {
    let mut guard = state.0.lock().await;
    let inner = guard.as_mut().ok_or("sidecar not connected")?;
    let msg = format!("{}\n", message);
    inner.child.write(msg.as_bytes()).map_err(|e| e.to_string())?;
    match inner.stdout_rx.recv().await {
        Some(line) => Ok(line),
        None => Err("sidecar disconnected".to_string()),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let (mut shell_rx, child) = app
                .shell()
                .sidecar("ppm-sidecar")
                .expect("ppm-sidecar not found in externalBin")
                .spawn()
                .expect("failed to spawn ppm-sidecar");

            let (tx, stdout_rx) = mpsc::unbounded_channel::<String>();

            tauri::async_runtime::spawn(async move {
                while let Some(event) = shell_rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line).trim().to_string();
                            if !text.is_empty() {
                                let _ = tx.send(text);
                            }
                        }
                        CommandEvent::Stderr(line) => {
                            log::warn!("sidecar stderr: {}", String::from_utf8_lossy(&line).trim());
                        }
                        CommandEvent::Terminated(payload) => {
                            log::info!("sidecar terminated: {:?}", payload.code);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            app.manage(SidecarState(Mutex::new(Some(SidecarInner { child, stdout_rx }))));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<SidecarState>();
                // Extract the inner value with the guard held in a nested block so
                // the MutexGuard (which borrows state) is dropped before state itself.
                let taken = {
                    match state.0.try_lock() {
                        Ok(mut guard) => guard.take(),
                        Err(_) => None,
                    }
                };
                if let Some(mut inner) = taken {
                    let _ = inner.child.write(b"{\"type\": \"shutdown\"}\n");
                    std::thread::sleep(std::time::Duration::from_millis(300));
                    let _ = inner.child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![send_to_sidecar])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
