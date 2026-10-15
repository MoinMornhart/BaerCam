// Update-Funktion: prüft GitHub-Releases (signiert) über das Tauri-Updater-Plugin.
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";

export type UpdateInfo = { available: false } | { available: true; version: string; notes: string; update: Update };

export async function checkForUpdate(): Promise<UpdateInfo> {
  if (!(window as any).__TAURI_INTERNALS__) return { available: false };
  const update = await check();
  if (!update) return { available: false };
  return { available: true, version: update.version, notes: update.body ?? "", update };
}

export async function installUpdate(update: Update, onProgress: (pct: number) => void): Promise<void> {
  let total = 0;
  let done = 0;
  await update.downloadAndInstall((ev) => {
    if (ev.event === "Started") total = ev.data.contentLength ?? 0;
    if (ev.event === "Progress") {
      done += ev.data.chunkLength;
      if (total) onProgress(Math.round((done / total) * 100));
    }
  });
  await relaunch();
}
