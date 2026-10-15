// Verbindung zum Python-Backend (JSON-RPC über WebSocket, siehe backend/baercam/server.py).
import { invoke } from "@tauri-apps/api/core";

type Pending = { resolve: (v: any) => void; reject: (e: Error) => void };
type Listener = (data: any) => void;

export type BackendState = "startet" | "verbunden" | "getrennt";

class Backend {
  private ws: WebSocket | null = null;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private listeners = new Map<string, Set<Listener>>();
  private stateListeners = new Set<(s: BackendState) => void>();
  state: BackendState = "startet";

  async connect(): Promise<void> {
    const info = await this.findBackend();
    const ws = new WebSocket(`ws://127.0.0.1:${info.port}/?token=${encodeURIComponent(info.token)}`);
    ws.onopen = () => this.setState("verbunden");
    ws.onmessage = (ev) => this.onMessage(JSON.parse(ev.data));
    ws.onclose = () => {
      this.setState("getrennt");
      for (const p of this.pending.values()) p.reject(new Error("Backend getrennt"));
      this.pending.clear();
      setTimeout(() => this.connect().catch(() => this.setState("getrennt")), 1500);
    };
    this.ws = ws;
  }

  // In Tauri liefert der Rust-Teil Port+Token; im reinen Browser (vite dev) ein fest gestartetes Dev-Backend.
  private async findBackend(): Promise<{ port: number; token: string }> {
    if ((window as any).__TAURI_INTERNALS__) {
      for (let i = 0; i < 100; i++) {
        const info = await invoke<{ port: number; token: string } | null>("backend_info");
        if (info) return info;
        await new Promise((r) => setTimeout(r, 200));
      }
      throw new Error("Backend startet nicht");
    }
    return { port: 47800, token: "dev" };
  }

  private onMessage(msg: any) {
    if (msg.event) {
      this.listeners.get(msg.event)?.forEach((fn) => fn(msg.data));
      return;
    }
    const p = this.pending.get(msg.id);
    if (!p) return;
    this.pending.delete(msg.id);
    if (msg.error) p.reject(Object.assign(new Error(msg.error.message), { code: msg.error.code }));
    else p.resolve(msg.result);
  }

  call<T = any>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return Promise.reject(new Error("Backend nicht verbunden"));
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }

  on(event: string, fn: Listener): () => void {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(fn);
    return () => this.listeners.get(event)?.delete(fn);
  }

  onState(fn: (s: BackendState) => void): () => void {
    this.stateListeners.add(fn);
    fn(this.state);
    return () => this.stateListeners.delete(fn);
  }

  private setState(s: BackendState) {
    this.state = s;
    this.stateListeners.forEach((fn) => fn(s));
  }
}

export const backend = new Backend();
