<script lang="ts">
  let { stage, text }: { stage: number; text: string } = $props();
</script>

<div class="card ph">
  <p>{text}</p>
  <p class="muted">Dieser Bereich wird in <strong>Etappe {stage}</strong> gebaut.</p>
</div>

<style>
  .ph { max-width: 640px; display: grid; gap: 6px; }
  p { margin: 0; }
</style>
