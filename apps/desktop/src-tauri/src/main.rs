#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{net::TcpListener, sync::Mutex};
use tauri::Manager;
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::{ShellExt, process::{CommandChild, CommandEvent}};

#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct EngineConnection { base_url: String, token: String }
struct EngineState { connection: EngineConnection, child: Mutex<Option<CommandChild>> }

#[tauri::command]
fn engine_connection(state: tauri::State<'_, EngineState>) -> EngineConnection { state.connection.clone() }

#[tauri::command]
fn open_source_url(app: tauri::AppHandle, url: String) -> Result<(), String> {
    let parsed = tauri::Url::parse(&url).map_err(|e| e.to_string())?;
    if !["https", "http"].contains(&parsed.scheme()) || !parsed.username().is_empty() || parsed.password().is_some() {
        return Err("Only public HTTP source links can be opened".into());
    }
    app.opener().open_url(url, None::<&str>).map_err(|e| e.to_string())
}

#[tauri::command]
async fn save_customer_export(app: tauri::AppHandle, content: String) -> Result<Option<String>, String> {
    if content.len() > 10 * 1024 * 1024 { return Err("Export exceeds 10 MB".into()); }
    tauri::async_runtime::spawn_blocking(move || {
        let selection = app.dialog().file().add_filter("CSV", &["csv"]).set_file_name("scansocial-customers.csv").blocking_save_file();
        match selection {
            Some(file) => {
                let path = file.into_path().map_err(|e| e.to_string())?;
                std::fs::write(&path, content).map_err(|e| e.to_string())?;
                Ok(Some(path.to_string_lossy().to_string()))
            },
            None => Ok(None),
        }
    }).await.map_err(|e| e.to_string())?
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
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
        .invoke_handler(tauri::generate_handler![engine_connection, open_source_url, save_customer_export])
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
