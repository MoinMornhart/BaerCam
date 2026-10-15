<script lang="ts">
  import { onMount } from "svelte";
  import { backend } from "../lib/backend";

  type Profile = { id: string; label: string; description: string; model_size: string; quantization: string; target_fps: number; prefer_online: boolean; avatar: string; render: string };
  type Gpu = { name: string; vendor: string; vram_gb: number | null; integrated: boolean };
  type State = {
    chosen: string; active: string | null; recommended: string | null; reasons: string[];
    benchmark: { cpuGflops: number } | null; profiles: Profile[];
    hardware: { os: string; cpu: string; cores: number; threads: number; ram_gb: number; gpus: Gpu[]; accelerators: string[] };
  };
  type Sample = { cpu: number; ram: number; ramFreeGb: number; gpu: { util: number; vramUsedGb: number; vramTotalGb: number } | null; fps?: { animation: number } };

  let st = $state<State | null>(null);
  let benching = $state(false);
  let samples = $state<Sample[]>([]);
  let suggestion = $state("");

  const accelNames: Record<string, string> = { cuda: "CUDA (NVIDIA)", directml: "DirectML", vulkan: "Vulkan", coreml: "Core ML", metal: "Metal", cpu: "CPU" };
  const avatarNames: Record<string, string> = { animaze: "Animaze", fallback3d: "Ersatz-Bär 3D", fallback2d: "Ersatz-Bär 2D" };

  async function bench() {
    benching = true;
    try { st = await backend.call("performance.benchmark"); } finally { benching = false; }
  }

  async function choose(id: string) {
    st = await backend.call("performance.setProfile", { id });
    suggestion = "";
  }

  function lowerProfile() {
    if (!st?.active) return;
    const order = ["ultra", "normal", "sparsam", "toaster"];
    const next = order[order.indexOf(st.active) + 1];
    if (next) choose(next);
  }

  onMount(() => {
    const offState = backend.onState(async (s) => {
      if (s !== "verbunden") return;
      st = await backend.call("performance.state");
      if (!st?.benchmark) bench();
    });
    const offSample = backend.on("perf.sample", (s: Sample) => { samples = [...samples.slice(-59), s]; });
    const offSuggest = backend.on("perf.suggestLower", (d) => { suggestion = d.reason; });
    return () => { offState(); offSample(); offSuggest(); };
  });

  const last = $derived(samples[samples.length - 1]);
  const meters = [
    { label: "CPU", key: (s: Sample) => s.cpu },
    { label: "RAM", key: (s: Sample) => s.ram },
    { label: "GPU", key: (s: Sample) => s.gpu?.util },
  ];
  function spark(list: Sample[], key: (s: Sample) => number | undefined): string {
    return list.map((s, i) => `${(i / 59) * 100},${30 - ((key(s) ?? 0) / 100) * 28}`).join(" ");
  }
</script>

{#if suggestion}
  <div class="card warn">
    <span>{suggestion} Ein niedrigeres Profil würde es flüssiger machen.</span>
    <button class="btn primary" onclick={lowerProfile}>Profil senken</button>
    <button class="btn" onclick={() => (suggestion = "")}>Ignorieren</button>
  </div>
{/if}

<div class="grid">
  <section class="card">
    <h2>Live-Auslastung</h2>
    <div class="meters">
      {#each meters as m (m.label)}
        {@const v = last ? m.key(last) : undefined}
        <div class="meter">
          <div class="mhead"><span>{m.label}</span><span class="mono">{v === undefined ? "–" : `${Math.round(v)} %`}</span></div>
          <svg viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><polyline points={spark(samples, m.key)} /></svg>
        </div>
      {/each}
      <div class="meter">
        <div class="mhead"><span>Animation</span><span class="mono">{last?.fps?.animation ?? 0} FPS</span></div>
        <p class="muted small">{last ? `${last.ramFreeGb} GB RAM frei` : ""}{last?.gpu ? ` · VRAM ${last.gpu.vramUsedGb}/${last.gpu.vramTotalGb} GB` : ""}</p>
      </div>
    </div>
  </section>

  {#if st}
    <section class="card">
      <div class="row between">
        <h2>Leistungsprofil</h2>
        <button class="btn" onclick={bench} disabled={benching}>{benching ? "Messe …" : "Benchmark neu starten"}</button>
      </div>
      {#if st.recommended}
        <p>Empfohlen: <strong>{st.profiles.find((p) => p.id === st!.recommended)?.label}</strong> – {st.reasons.join(" ")}</p>
      {/if}
      <div class="profiles" role="radiogroup" aria-label="Leistungsprofil">
        <button class="prof" role="radio" aria-checked={st.chosen === "auto"} class:on={st.chosen === "auto"} onclick={() => choose("auto")}>
          <strong>Automatisch</strong><span class="muted">BärCam wählt passend zur Hardware.</span>
        </button>
        {#each st.profiles as p (p.id)}
          <button class="prof" role="radio" aria-checked={st.chosen === p.id} class:on={st.chosen === p.id} onclick={() => choose(p.id)}>
            <strong>{p.label}{st.active === p.id ? " ✓" : ""}</strong>
            <span class="muted">{p.description}</span>
            <span class="tags"><i>{p.model_size}</i><i>{p.quantization.toUpperCase()}</i><i>{p.target_fps} FPS</i><i>{avatarNames[p.avatar]}</i>{#if p.prefer_online}<i>online</i>{/if}</span>
          </button>
        {/each}
      </div>
    </section>

    <section class="card">
      <h2>Dein Rechner</h2>
      <dl>
        <dt>System</dt><dd>{st.hardware.os}</dd>
        <dt>Prozessor</dt><dd>{st.hardware.cpu} · {st.hardware.cores} Kerne / {st.hardware.threads} Threads{st.benchmark ? ` · ${st.benchmark.cpuGflops} GFLOPS` : ""}</dd>
        <dt>Arbeitsspeicher</dt><dd>{st.hardware.ram_gb} GB</dd>
        <dt>Grafik</dt><dd>{#each st.hardware.gpus as g}{g.name}{g.vram_gb ? ` (${g.vram_gb} GB)` : ""}{g.integrated ? " · integriert" : ""}<br />{:else}keine erkannt{/each}</dd>
        <dt>Beschleunigung</dt><dd>{st.hardware.accelerators.map((a) => accelNames[a] ?? a).join(" → ")}</dd>
      </dl>
    </section>
  {/if}
</div>

<style>
  .grid { display: grid; gap: 16px; max-width: 900px; }
  section { display: grid; gap: 12px; }
  h2 { font-size: 16px; } p { margin: 0; }
  .row { display: flex; gap: 10px; align-items: center; } .between { justify-content: space-between; }
  .warn { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; border-color: var(--warn); margin-bottom: 16px; max-width: 900px; }
  .meters { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
  .meter { background: var(--panel-2); border-radius: 8px; padding: 10px 12px; display: grid; gap: 6px; }
  .mhead { display: flex; justify-content: space-between; font-size: 13px; }
  .mono { font-variant-numeric: tabular-nums; }
  svg { width: 100%; height: 30px; }
  polyline { fill: none; stroke: var(--honey); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
  .small { font-size: 12px; }
  .profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }
  .prof { all: unset; box-sizing: border-box; cursor: pointer; background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; padding: 12px; display: grid; gap: 6px; align-content: start; }
  .prof:hover { border-color: var(--bark); }
  .prof.on { border-color: var(--honey); box-shadow: inset 0 0 0 1px var(--honey); }
  .prof:focus-visible { outline: 2px solid var(--honey); }
  .prof .muted { font-size: 12.5px; }
  .tags { display: flex; flex-wrap: wrap; gap: 4px; }
  .tags i { font-style: normal; font-size: 11px; font-family: var(--mono); border: 1px solid var(--line); border-radius: 99px; padding: 1px 7px; color: var(--muted); }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; font-size: 13.5px; }
  dt { color: var(--muted); } dd { margin: 0; }
</style>
