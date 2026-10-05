#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{net::TcpListener, sync::Mutex};
use tauri::Manager;
use tauri_plugin_shell::{ShellExt, process::{CommandChild, CommandEvent}};

#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct EngineConnection { base_url: String, token: String }
struct EngineState { connection: EngineConnection, child: Mutex<Option<CommandChild>> }

#[tauri::command]
fn engine_connection(state: tauri::State<'_, EngineState>) -> EngineConnection { state.connection.clone() }

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let listener = TcpListener::bind("127.0.0.1:0")?;
            let port = listener.local_addr()?.port();
            let mut random = [0u8; 32];
            getrandom::getrandom(&mut random).map_err(|e| std::io::Error::other(e.to_string()))?;
            let token: String = random.iter().map(|b| format!("{b:02x}")).collect();
            let data_dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir)?;
            // Pass secrets through the child environment instead of process arguments.
            let command = app.shell().sidecar("scansocial-engine")?
                .args(["--port", &port.to_string()])
                .env("SCANSOCIAL_SESSION_TOKEN", &token)
                .env("SCANSOCIAL_DATA_DIR", data_dir.to_string_lossy().to_string());
            drop(listener);
            let (mut events, child) = command.spawn()?;
            app.manage(EngineState { connection: EngineConnection { base_url: format!("http://127.0.0.1:{port}"), token }, child: Mutex::new(Some(child)) });
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Error(error) = event { eprintln!("Engine process: {error}"); }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_connection])
        .build(tauri::generate_context!())
        .expect("Could not initialize ScanSocial desktop");
    app.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<EngineState>() {
                if let Some(child) = state.child.lock().ok().and_then(|mut child| child.take()) {
                    let _ = child.kill();
                }
            }
        }
    });
}
