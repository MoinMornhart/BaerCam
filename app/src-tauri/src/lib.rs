//! Tauri-Hülle: startet das Python-Backend als Kindprozess und reicht Port + Token an die Oberfläche.

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use tauri::{Manager, RunEvent, State};

#[derive(Clone, Serialize, Deserialize)]
struct BackendInfo {
    port: u16,
    token: String,
    version: String,
}

#[derive(Default)]
struct Backend {
    info: Mutex<Option<BackendInfo>>,
    child: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_info(state: State<'_, std::sync::Arc<Backend>>) -> Option<BackendInfo> {
    state.info.lock().unwrap().clone()
}

/// Release: die mitgelieferte Sidecar-EXE neben der App.
/// Entwicklung: `python -m baercam` aus BAERCAM_PYTHON bzw. dem Dev-venv.
fn backend_command() -> Command {
    let exe_dir = std::env::current_exe().ok().and_then(|p| p.parent().map(PathBuf::from));
    let sidecar_name = if cfg!(windows) { "baercam-backend.exe" } else { "baercam-backend" };
    if let Some(sidecar) = exe_dir.map(|d| d.join(sidecar_name)).filter(|p| p.exists()) {
        return Command::new(sidecar);
    }
    let python = std::env::var("BAERCAM_PYTHON").unwrap_or_else(|_| {
        if cfg!(windows) {
            let base = std::env::var("LOCALAPPDATA").unwrap_or_default();
            format!("{base}\\BaerCam\\dev-venv\\Scripts\\python.exe")
        } else {
            "python3".into()
        }
    });
    let mut cmd = Command::new(python);
    cmd.args(["-m", "baercam"]);
    cmd
}

fn spawn_backend(state: std::sync::Arc<Backend>) {
    let mut cmd = backend_command();
    cmd.stdout(Stdio::piped()).stderr(Stdio::null()).stdin(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Backend konnte nicht gestartet werden: {e}");
            return;
        }
    };
    let stdout = child.stdout.take().expect("stdout");
    *state.child.lock().unwrap() = Some(child);

    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(json) = line.strip_prefix("BAERCAM_READY ") {
                if let Ok(info) = serde_json::from_str::<BackendInfo>(json) {
                    *state.info.lock().unwrap() = Some(info);
                }
            }
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend = std::sync::Arc::new(Backend::default());
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(backend.clone())
        .invoke_handler(tauri::generate_handler![backend_info])
        .setup(move |_app| {
            spawn_backend(backend.clone());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("BärCam konnte nicht starten");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            let state = handle.state::<std::sync::Arc<Backend>>();
            let child = state.child.lock().unwrap().take();
            if let Some(mut child) = child {
                let _ = child.kill();
            }
        }
    });
}
