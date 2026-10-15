<script lang="ts">
  import { backend } from "../lib/backend";
  import { checkForUpdate, installUpdate, type UpdateInfo } from "../lib/updater";
  import { getVersion } from "@tauri-apps/api/app";
  import { onMount } from "svelte";

  let { reducedEffects = $bindable(false) }: { reducedEffects: boolean } = $props();

  let appVersion = $state("–");
  let status = $state("");
  let busy = $state(false);
  let found = $state<UpdateInfo | null>(null);
  let progress = $state(0);

  onMount(async () => {
    if ((window as any).__TAURI_INTERNALS__) appVersion = await getVersion();
  });

  async function toggleEffects() {
    reducedEffects = !reducedEffects;
    await backend.call("settings.update", { patch: { ui: { reducedEffects } } }).catch(() => {});
  }

  async function check() {
    busy = true;
    status = "Suche nach Updates …";
    try {
      found = await checkForUpdate();
      status = found.available ? `Version ${found.version} ist verfügbar.` : "BärCam ist aktuell.";
    } catch (e) {
      status = `Update-Prüfung fehlgeschlagen: ${(e as Error).message ?? e}`;
    } finally {
      busy = false;
    }
  }

  async function install() {
    if (!found?.available) return;
    busy = true;
    status = "Lade Update …";
    try {
      await installUpdate(found.update, (p) => (progress = p));
    } catch (e) {
      status = `Update fehlgeschlagen: ${(e as Error).message ?? e}`;
      busy = false;
    }
  }
</script>

<div class="grid">
  <section class="card">
    <h2>Updates</h2>
    <p class="muted">Installierte Version: <span class="mono">{appVersion}</span></p>
    <div class="row">
      <button class="btn" onclick={check} disabled={busy}>Nach Updates suchen</button>
      {#if found?.available}
        <button class="btn primary" onclick={install} disabled={busy}>Jetzt aktualisieren</button>
      {/if}
    </div>
    {#if status}<p aria-live="polite">{status}{progress ? ` (${progress} %)` : ""}</p>{/if}
    {#if found?.available && found.notes}<pre class="notes">{found.notes}</pre>{/if}
  </section>

  <section class="card">
    <h2>Darstellung</h2>
    <label class="row">
      <input id="reduced-effects" type="checkbox" checked={reducedEffects} onchange={toggleEffects} />
      Sparmodus für die Oberfläche (keine Animationen und Schatten)
    </label>
  </section>
</div>

<style>
  .grid { display: grid; gap: 16px; max-width: 680px; }
  section { display: grid; gap: 10px; }
  h2 { font-size: 16px; }
  p { margin: 0; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .notes { white-space: pre-wrap; background: var(--panel-2); padding: 10px; border-radius: 8px; margin: 0; font-family: var(--mono); font-size: 12px; }
</style>
