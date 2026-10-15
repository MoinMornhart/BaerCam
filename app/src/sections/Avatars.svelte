<script lang="ts">
  import { onMount } from "svelte";
  import { backend } from "../lib/backend";

  type Avatar = { name: string; label: string; icon: string };

  let connected = $state(false);
  let avatars = $state<Avatar[]>([]);
  let loading = $state(false);
  let busy = $state("");
  let message = $state("");

  function normalize(raw: any[]): Avatar[] {
    return raw.map((r, i) => {
      if (typeof r === "string") return { name: r, label: r, icon: "" };
      const name = r.itemName ?? r.name ?? `avatar-${i}`;
      return { name, label: r.friendlyName ?? r.name ?? name, icon: r.icon ?? "" };
    });
  }

  async function load() {
    loading = true;
    message = "";
    try {
      avatars = normalize(await backend.call("animaze.avatars", { withIcons: true }));
      if (!avatars.length) message = "Animaze hat keine Avatare gemeldet.";
    } catch (e) {
      message = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  async function pick(a: Avatar) {
    busy = a.name;
    try {
      await backend.call("animaze.loadAvatar", { name: a.name });
      message = `„${a.label}“ wird in Animaze geladen.`;
    } catch (e) {
      message = (e as Error).message;
    } finally {
      busy = "";
    }
  }

  onMount(() => {
    const check = async () => {
      const s = await backend.call("animaze.status");
      const was = connected;
      connected = s.connected;
      if (connected && !was) load();
    };
    const offState = backend.onState((s) => s === "verbunden" && check());
    const offEvt = backend.on("animaze.status", check);
    return () => { offState(); offEvt(); };
  });

  const src = (icon: string) => (icon.startsWith("data:") ? icon : `data:image/png;base64,${icon}`);
</script>

{#if !connected}
  <div class="card">
    <p>Avatare werden aus Animaze geladen, sobald BärCam verbunden ist (siehe „Animaze-Verbindung“).</p>
    <p class="muted">Ohne Animaze gibt es ab Etappe 4 den eingebauten Ersatz-Bären.</p>
  </div>
{:else}
  <div class="bar">
    <button class="btn" onclick={load} disabled={loading}>{loading ? "Lade …" : "Neu laden"}</button>
    <span class="muted" aria-live="polite">{message}</span>
  </div>
  <div class="grid">
    {#each avatars as a (a.name)}
      <button class="tile" onclick={() => pick(a)} disabled={busy === a.name}>
        {#if a.icon}<img src={src(a.icon)} alt="" loading="lazy" />{:else}<div class="noimg">🐻</div>{/if}
        <span>{a.label}</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .card { display: grid; gap: 6px; max-width: 640px; } p { margin: 0; }
  .bar { display: flex; gap: 12px; align-items: center; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
  .tile { all: unset; cursor: pointer; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; display: grid; }
  .tile:hover { border-color: var(--honey); }
  .tile:focus-visible { outline: 2px solid var(--honey); }
  .tile:disabled { opacity: .6; }
  img, .noimg { width: 100%; aspect-ratio: 1; object-fit: cover; background: var(--panel-2); display: grid; place-items: center; font-size: 40px; }
  span { padding: 8px 10px; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
