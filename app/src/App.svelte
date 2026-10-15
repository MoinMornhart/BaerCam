<script lang="ts">
  import { onMount } from "svelte";
  import { backend, type BackendState } from "./lib/backend";
  import Placeholder from "./sections/Placeholder.svelte";
  import Settings from "./sections/Settings.svelte";
  import Animaze from "./sections/Animaze.svelte";
  import Avatars from "./sections/Avatars.svelte";
  import Performance from "./sections/Performance.svelte";

  type Section = { id: string; label: string; icon: string; stage: number; text: string };
  const sections: Section[] = [
    { id: "animaze", label: "Animaze-Verbindung", icon: "M4 12a8 8 0 0 1 16 0M8 12a4 4 0 0 1 8 0M12 12v6", stage: 1,
      text: "Hier verbindet sich BärCam mit Animaze (API, VMC, Programmable Tracker) und zeigt den Status." },
    { id: "create", label: "Animation erstellen", icon: "M5 19l4-10 4 6 3-4 3 8", stage: 2,
      text: "Beliebigen Text eingeben – BärCam erzeugt daraus Bewegung, Mimik und Sprache." },
    { id: "library", label: "Meine Animationen", icon: "M4 6h16M4 12h16M4 18h10", stage: 2,
      text: "Gespeicherte, aufgenommene und importierte Animationen (BVH/FBX/GLB)." },
    { id: "voice", label: "Meine Stimme", icon: "M12 4v10M8 9v4a4 4 0 0 0 8 0V9M12 18v2", stage: 3,
      text: "Eigene Stimme aufnehmen, Stimmprofil erstellen und Stimmeffekte wählen." },
    { id: "avatars", label: "Avatare", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20a8 8 0 0 1 16 0", stage: 1,
      text: "Animaze-Avatare mit Vorschaubild laden – oder den eingebauten Ersatz-Bären nutzen." },
    { id: "providers", label: "KI-Anbieter", icon: "M7 7h10v10H7zM4 10h3M4 14h3M17 10h3M17 14h3M10 4v3M14 4v3M10 17v3M14 17v3", stage: 2,
      text: "Beliebige KI-APIs eintragen: OpenAI-kompatibel (NVIDIA NIM, OpenRouter, Groq …), Claude, Gemini, Ollama, LM Studio." },
    { id: "performance", label: "Leistung", icon: "M4 18a8 8 0 1 1 16 0M12 18l4-6", stage: 1,
      text: "Hardware-Erkennung, Benchmark und Leistungsprofil (Ultra, Normal, Sparsam, Toaster) mit Live-Anzeige." },
    { id: "settings", label: "Einstellungen", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-1-3-2 .5-1.5-1.5L17 5l-3-1-1 2h-2L10 4 7 5l.5 2L6 8.5 4 8l-1 3 2 1v0l-2 1 1 3 2-.5L7.5 17 7 19l3 1 1-2h2l1 2 3-1-.5-2 1.5-1.5 2 .5 1-3z", stage: 0, text: "" },
  ];

  const fromHash = location.hash.slice(1);
  let active = $state(sections.some((s) => s.id === fromHash) ? fromHash : "animaze");
  let backendState = $state<BackendState>("startet");
  let version = $state("");
  let reducedEffects = $state(false);
  const current = $derived(sections.find((s) => s.id === active)!);

  onMount(() => {
    const off = backend.onState(async (s) => {
      backendState = s;
      if (s === "verbunden") {
        version = (await backend.call("system.ping")).version;
        reducedEffects = (await backend.call("settings.get")).ui.reducedEffects;
      }
    });
    backend.connect().catch(() => (backendState = "getrennt"));
    return off;
  });

  const dot = $derived(backendState === "verbunden" ? "ok" : backendState === "startet" ? "warn" : "bad");
</script>

<div class="shell" class:sparmodus={reducedEffects}>
  <nav aria-label="Bereiche">
    <div class="brand">
      <img src="/logo.svg" alt="" width="34" height="34" />
      <span>BärCam</span>
    </div>
    <ul>
      {#each sections as s (s.id)}
        <li>
          <button class:active={active === s.id} aria-current={active === s.id ? "page" : undefined} onclick={() => (active = s.id)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={s.icon} /></svg>
            {s.label}
          </button>
        </li>
      {/each}
    </ul>
    <div class="foot">
      <span class="dot {dot}"></span>
      <span>Backend {backendState}{version ? ` · v${version}` : ""}</span>
    </div>
  </nav>

  <main>
    <header><h1>{current.label}</h1></header>
    {#if active === "settings"}
      <Settings bind:reducedEffects />
    {:else if active === "animaze"}
      <Animaze />
    {:else if active === "avatars"}
      <Avatars />
    {:else if active === "performance"}
      <Performance />
    {:else}
      <Placeholder stage={current.stage} text={current.text} />
    {/if}
  </main>
</div>

<style>
  .shell { display: grid; grid-template-columns: 232px 1fr; height: 100%; }
  nav { background: var(--panel); border-right: 1px solid var(--line); display: flex; flex-direction: column; padding: 16px 10px; gap: 14px; }
  .brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 10px; font-size: 20px; font-weight: 750; letter-spacing: -.01em; }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
  li button { all: unset; box-sizing: border-box; width: 100%; display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; cursor: pointer; color: var(--muted); transition: background .12s; }
  li button:hover { background: var(--panel-2); color: var(--fg); }
  li button.active { background: var(--panel-2); color: var(--fg); box-shadow: inset 3px 0 0 var(--honey); }
  li button:focus-visible { outline: 2px solid var(--honey); }
  svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }
  .foot { margin-top: auto; display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); padding: 0 8px; }
  main { overflow: auto; padding: 26px 32px; display: grid; align-content: start; gap: 20px; }
  h1 { font-size: 24px; }
  @media (max-width: 760px) { .shell { grid-template-columns: 64px 1fr; } .brand span, li button { font-size: 0; } li button { justify-content: center; } }
</style>
