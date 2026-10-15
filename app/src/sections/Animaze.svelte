<script lang="ts">
  import { onMount } from "svelte";
  import { backend } from "../lib/backend";

  type Status = { connected: boolean; url: string; error: string; installed: boolean; running: boolean; platformSupported: boolean };
  type Item = { label: string; value: string | number };

  let status = $state<Status | null>(null);
  let cfg = $state({ host: "127.0.0.1", apiPort: 9000, vmcPort: 39539, trackerPort: 9003 });
  let saved = $state("");
  let lists = $state<Record<string, Item[]>>({});
  let listError = $state("");
  let clips = $state<{ id: string; name: string }[]>([]);
  let playing = $state("");
  let broadcastOn = $state(false);

  const kinds = [
    { key: "emotes", trigger: "emote", label: "Emotes" },
    { key: "specialActions", trigger: "specialAction", label: "Special Actions" },
    { key: "poses", trigger: "pose", label: "Posen" },
    { key: "idles", trigger: "idle", label: "Idle-Animationen" },
  ];

  function toItems(kind: string, raw: any[]): Item[] {
    return raw.map((r, i) => {
      if (typeof r === "string") return { label: r, value: kind === "emotes" ? r : i };
      const label = r.friendlyName ?? r.animName ?? r.name ?? r.itemName ?? `#${i}`;
      const value = kind === "emotes" ? (r.itemName ?? r.name ?? label) : (r.index ?? i);
      return { label, value };
    });
  }

  async function refreshStatus() {
    status = await backend.call("animaze.status");
  }

  async function loadLists() {
    listError = "";
    const out: Record<string, Item[]> = {};
    for (const k of kinds) {
      try {
        out[k.key] = toItems(k.key, await backend.call("animaze.list", { kind: k.key }));
      } catch (e) {
        listError = (e as Error).message;
      }
    }
    lists = out;
  }

  async function save() {
    cfg = await backend.call("animaze.configure", { ...cfg });
    saved = "Gespeichert – BärCam verbindet sich neu.";
    setTimeout(() => (saved = ""), 2500);
  }

  async function trigger(kind: string, value: string | number) {
    try {
      await backend.call("animaze.trigger", { kind, value });
    } catch (e) {
      listError = (e as Error).message;
    }
  }

  async function play(id: string) {
    playing = id;
    await backend.call("motion.play", { id });
    setTimeout(() => (playing = ""), 2600);
  }

  async function toggleBroadcast() {
    broadcastOn = !broadcastOn;
    await backend.call("animaze.broadcast", { on: broadcastOn }).catch((e) => (listError = e.message));
  }

  onMount(() => {
    const offState = backend.onState(async (s) => {
      if (s !== "verbunden") return;
      cfg = (await backend.call("settings.get")).animaze;
      clips = await backend.call("motion.testClips");
      await refreshStatus();
      if (status?.connected) loadLists();
    });
    const offEvt = backend.on("animaze.status", async () => {
      await refreshStatus();
      if (status?.connected) loadLists();
    });
    const poll = setInterval(() => backend.state === "verbunden" && refreshStatus(), 5000);
    return () => { offState(); offEvt(); clearInterval(poll); };
  });

  const tone = $derived(!status ? "warn" : status.connected ? "ok" : "bad");
</script>

<div class="grid">
  <section class="card status">
    <div class="row">
      <span class="dot {tone}"></span>
      <strong>{!status ? "Prüfe …" : status.connected ? "Mit Animaze verbunden" : "Nicht verbunden"}</strong>
      <span class="muted mono">{status?.url ?? ""}</span>
    </div>
    {#if status && !status.connected}
      <div class="help">
        {#if !status.platformSupported}
          <p>Animaze gibt es nur für Windows. BärCam nutzt hier den eingebauten Ersatz-Bären (Etappe 4).</p>
        {:else if !status.installed}
          <p>Animaze wurde nicht gefunden. Installiere es über <a href="https://store.steampowered.com/app/1364390/Animaze_by_FaceRig/" target="_blank" rel="noreferrer">Steam</a> – oder nutze den eingebauten Ersatz-Bären.</p>
        {:else if !status.running}
          <p>Animaze ist installiert, läuft aber nicht. Starte Animaze – BärCam verbindet sich dann von selbst.</p>
        {:else}
          <p><strong>Animaze läuft, aber die API ist aus.</strong> So schaltest du sie ein:</p>
          <ol>
            <li>In Animaze oben auf <b>Settings</b> (Zahnrad) klicken.</li>
            <li><b>Animaze API</b> öffnen und <b>Enabled</b> einschalten.</li>
            <li>Port muss <b>{cfg.apiPort}</b> sein (oder unten anpassen).</li>
          </ol>
          <p class="muted">BärCam versucht es alle paar Sekunden neu.</p>
        {/if}
      </div>
    {/if}
  </section>

  <section class="card">
    <h2>Verbindung</h2>
    <div class="form">
      <label>Adresse <input id="az-host" bind:value={cfg.host} /></label>
      <label>API-Port <input id="az-api" type="number" bind:value={cfg.apiPort} /></label>
      <label>VMC-Port <input id="az-vmc" type="number" bind:value={cfg.vmcPort} /></label>
      <label>Tracker-Port <input id="az-tracker" type="number" bind:value={cfg.trackerPort} /></label>
    </div>
    <div class="row"><button class="btn" onclick={save}>Speichern</button><span class="muted">{saved}</span></div>
    <details>
      <summary>So aktivierst du VMC und den Programmable Tracker in Animaze</summary>
      <ol>
        <li><b>Körper (VMC):</b> Settings → Advanced Tracking Configuration → Select Trackers → <b>VMC Body Tracker</b>, IP {cfg.host}, Port {cfg.vmcPort}, <b>Connect</b>.</li>
        <li><b>Mimik & Finger:</b> dort auch den <b>Programmable Tracker</b> aktivieren, IP {cfg.host}, Port {cfg.trackerPort}.</li>
        <li>Die Webcam bleibt aktiv – BärCam blendet seine Bewegungen nur darüber und gibt danach zurück.</li>
      </ol>
    </details>
  </section>

  <section class="card">
    <h2>Testbewegungen</h2>
    <p class="muted">Prüft, ob Körper (VMC) und Mimik/Finger (Programmable Tracker) in Animaze ankommen. Das sind nur Tests – ab Etappe 2 erzeugt die KI beliebige Bewegungen.</p>
    <div class="chips">
      {#each clips as c (c.id)}
        <button class="btn" class:primary={playing === c.id} onclick={() => play(c.id)}>{c.name}</button>
      {/each}
      <button class="btn" onclick={() => backend.call("motion.stop")}>Stopp</button>
    </div>
  </section>

  {#if status?.connected}
    <section class="card">
      <div class="row between">
        <h2>Animaze steuern</h2>
        <div class="row">
          <button class="btn" onclick={() => backend.call("animaze.calibrate")}>Tracking kalibrieren</button>
          <button class="btn" class:primary={broadcastOn} onclick={toggleBroadcast}>Virtuelle Kamera {broadcastOn ? "aus" : "an"}</button>
        </div>
      </div>
      {#if listError}<p class="err">{listError}</p>{/if}
      {#each kinds as k (k.key)}
        {#if lists[k.key]?.length}
          <h3>{k.label}</h3>
          <div class="chips">
            {#each lists[k.key] as it (it.value)}
              <button class="btn small" onclick={() => trigger(k.trigger, it.value)}>{it.label}</button>
            {/each}
          </div>
        {/if}
      {/each}
    </section>
  {/if}
</div>

<style>
  .grid { display: grid; gap: 16px; max-width: 860px; }
  section { display: grid; gap: 10px; }
  h2 { font-size: 16px; } h3 { font-size: 13px; color: var(--muted); font-weight: 600; margin-top: 4px; }
  p { margin: 0; } ol { margin: 0; padding-left: 20px; display: grid; gap: 4px; }
  a { color: var(--honey); }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .between { justify-content: space-between; }
  .status strong { font-size: 15px; }
  .help { background: var(--panel-2); border-radius: 8px; padding: 12px 14px; display: grid; gap: 8px; }
  .form { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  label { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
  input { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; color: var(--fg); font: inherit; }
  details summary { cursor: pointer; color: var(--muted); }
  details ol { margin-top: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .small { padding: 4px 10px; font-size: 13px; }
  .err { color: var(--bad); }
</style>
