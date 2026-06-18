# VerticalFarm Edge Inference System

This directory contains the **split inference stack** for VerticalFarm: a Rust TCP server on a dedicated GPU device (e.g. Jetson Orin Nano) and a Python **workflow proxy** on the business device that reuses the full `llm/` agent pipeline.

The design goal is to complete a full multi-stage control cycle within a **15-minute closed loop** while keeping each inference cycle under **~70 seconds** on constrained edge hardware — without loading a model on the gateway host.

---

## System Overview


| Process | Location | Role |
|---------|----------|------|
| **vf-proxy** | Business device (gateway / control host) | Runs `LocalWorkflow`, playbook RAG, simulation, safety shield. Sends LLM calls to the inference device. |
| **vf-server** | Dedicated inference device | Owns the model, semantic cache, KV-cache planning, and **strictly serial** GPU inference. |
| **llm/** | Imported by vf-proxy | Existing prompts, schemas, and workflow stages (`diagnosis`, `planning`, `decision`, etc.). |

The proxy is **not** a second agent implementation. It is a drop-in `BaseLLMClient` backend (`LLMProvider.VF_SERVER`) that makes `llm/demo.py` and `LocalWorkflow` work against a remote model.

---

## How It Works

### 1. Control cycle (business device)

1. Sensor state arrives (JSON, same shape as `fixtures/esp32_state.json`).
2. **vf-proxy** builds `LocalLLMInput` and opens a **workflow session** (`vf_workflow_session`) with a unique `cycle_id`.
3. `LocalWorkflow` runs its normal DAG: playbook RAG → diagnosis → planning → side effects → simulation → decision → final command.
4. Every LLM step calls `VFServerClient.run_chain()` or `run_messages()` — the same interface used by Ollama/OpenAI clients.
5. Non-LLM steps (simulation, safety shield, playbook retrieval) run **locally** on the business device.
6. At cycle end, the proxy sends `cycle_end` to release server-side KV state.

### 2. Proxy → server (each LLM call)

For every LLM step, the proxy transforms the LangChain prompt into a structured infer request:

1. **Prompt splitting** — the full prompt is divided into three logical segments:
   - **Static prefix** — role, goals, and safety rules (~80 tokens). Identical across all stages in a workflow cycle.
   - **Sensor state** — live environment data (temperature, humidity, photoperiod, trends).
   - **Instruction** — stage-specific task text (diagnosis, planning, decision, etc.).
2. **Stage detection** — the workflow stage is inferred from prompt markers (e.g. a decision-making header maps to the `decision` stage).
3. **State signature** — coarse buckets (2°C temperature bands, 10% humidity bands, trend magnitude) used for semantic cache lookup.
4. The request is sent over TCP; the JSON response is parsed back into an assistant message for the workflow.

### 3. Server-side inference (inference device)

For each infer request, the server:

1. Checks the **semantic cache** (in-memory, no external store).
2. On **cache hit** — returns the stored JSON immediately (~1 ms). The GPU stays idle.
3. On **cache miss** — consults the **KV manager** to decide how much of the prompt needs prefill, runs generation through the backend (llama.cpp in production, fixtures in mock mode), and stores the result in the semantic cache (default TTL 120 min).

**Serial guarantee:** only one infer runs at a time per server process. Heartbeat and cache-control messages bypass the GPU path and are handled instantly.

---

## Prefill Optimization

A single workflow cycle runs multiple LLM stages (diagnosis, planning, assessment, decision, and so on). Each stage would normally re-process the entire prompt from scratch. The stack uses three complementary layers to avoid redundant work.

### Layer 1 — Semantic cache (skip all prefill and decode)

Before any GPU work, the server checks whether an identical question was already answered under similar greenhouse conditions.

The cache key combines the workflow stage, model identifier, and a coarse **state signature**: internal and external temperature buckets, humidity bucket, photoperiod, temperature trend, crop, and growth stage. When the environment is stable across 15-minute control cycles, many stages produce the same JSON output as a previous run.

On a **cache hit**, the server returns the stored answer in about one millisecond. No tokenization, no prefill, and no decode occur. Response metrics report zero prefill tokens. This is the strongest optimization and targets a steady-state hit rate of at least 40% in maintenance conditions.

The cache is invalidated when:

- The entry exceeds its TTL (default 120 minutes).
- A previously stable maintenance diagnosis sees a sharp temperature rise (more than +1.5°C per 15 minutes).
- The photoperiod flips (lights on ↔ off), which triggers a full cache flush.

Because the cache key includes the model name, a result produced by an OOM fallback model does not collide with a primary-model entry.

### Layer 2 — Prompt splitting (prepare for KV reuse)

Even on a cache miss, not every part of the prompt changes between stages. The proxy sends three segments rather than one monolithic string:

| Segment | Content | Changes per stage? |
|---------|---------|-------------------|
| Static prefix | Role, objectives, safety rules | No — same for the whole cycle |
| Instruction | Stage-specific task description | Yes |
| Sensor state | Live sensor and forecast block | Usually yes |

The server treats the **static prefix** and the **variable portion** (instruction plus sensor state) differently. The static block is the expensive part to repeat; the variable portion is smaller and must be refreshed each stage.

### Layer 3 — Per-cycle KV planning

Within one workflow cycle, all stages share the same static prefix but differ in instruction and sensor data. The server tracks KV state keyed by **cycle ID** (assigned when the proxy opens a workflow session).

**First LLM call in a cycle:**

- Prefill the static prefix into the model's KV cache.
- Save a snapshot of the KV state after the static prefix is processed.
- Prefill the variable portion for the current stage.
- Decode (generate) the stage output.

**Subsequent LLM calls in the same cycle:**

- Restore the saved KV snapshot (static prefix already represented in cache).
- Prefill only the variable portion for the new stage.
- Decode the stage output.

**End of cycle:**

- The proxy sends a cycle-end message.
- The server drops KV tracking and snapshots for that cycle ID.

This avoids re-processing roughly 80 tokens of static context on every stage after the first. For a typical eight-stage workflow, that saves about **80 × (N − 1)** tokens of redundant prefill per cycle — on the order of **24% less prefill work** compared to naively re-sending the full prompt each time.

### What this does not optimize

- **Decode cost** — each stage still generates new tokens. KV planning reduces prefill, not generation length.
- **Cross-cycle reuse** — KV snapshots are scoped to a single cycle ID. The next 15-minute control loop starts fresh unless the semantic cache hits.
- **Parallel stages** — inference is strictly serial; there is no batching of multiple stages into one forward pass.

See [Power and Compute Control](#power-and-compute-control) for how these optimizations fit into the broader energy and latency budget on Jetson hardware.

---

## TCP Protocol

Framing: **4-byte big-endian length** + UTF-8 JSON body. Schema: [`proto/schema.json`](proto/schema.json).

| Message | Direction | Purpose |
|---------|-----------|---------|
| `heartbeat` | Client → Server | Keep-alive + server health check |
| `heartbeat_ack` | Server → Client | `server_uptime_ms`, `model_ready` |
| `infer` | Client → Server | Single LLM inference request |
| `infer_response` | Server → Client | Output JSON + `cache_hit` + latency metrics |
| `flush_cache` | Client → Server | Clear semantic cache (e.g. photoperiod change) |
| `cycle_end` | Client → Server | Release KV state for a workflow cycle |
| `error` | Either | Error code and message |

---

## Heartbeat

Heartbeats keep the TCP session alive and let the proxy know the inference device is ready before sending expensive workflow cycles.

### Client side (`llm/clients/vf_tcp.py`)

- Started automatically when `VFServerClient.connect()` is called.
- Background **daemon thread** sends `heartbeat` every **10 seconds** (`VF_HEARTBEAT_SEC`).
- Payload:
  ```json
  {"type": "heartbeat", "client_id": "vf-proxy-abc123", "timestamp": "2026-06-18T12:00:00+00:00"}
  ```
- On success, expects:
  ```json
  {"type": "heartbeat_ack", "server_uptime_ms": 123456, "model_ready": true}
  ```
- If `model_ready` is `false` (model still loading/warming up), the client waits an extra second before workflow infer calls.
- On failure (network blip, server restart), the client logs the error and **attempts reconnect** on the next interval.
- All TCP I/O (heartbeat + infer) shares one **thread lock** so frames are never interleaved on the wire.

### Server side (`vf-server/src/queue.rs`)

- Heartbeat is handled **without** acquiring `infer_lock` — it never blocks behind a running inference.
- Response is built from `InferenceService::heartbeat_ack()` (uptime since process start + backend `is_ready()` flag).
- The server does **not** disconnect idle clients; heartbeats are advisory. Production deployments can add firewall idle timeouts independently.

### Why heartbeats matter on Jetson

- Confirms the model finished warmup (`model_ready: true`) after boot — avoids a 3–5 s cold-start surprise on the first real cycle.
- Detects network partition early so the gateway can retry or fall back before the 15-minute control deadline.
- Keeps NAT / middlebox mappings warm on long idle periods between 15-minute control cycles.

---

## Power and Compute Control

Edge deployment targets passive cooling and unified CPU/GPU memory. The stack reduces energy draw through **software scheduling** rather than dynamic voltage scaling in application code.

### 1. Skip GPU work (semantic cache)

- Stable greenhouse states repeat across 15-minute cycles (same temp/humidity buckets, same photoperiod).
- Server keys cache entries by `sha256(stage | temp_bucket | humidity_bucket | photoperiod | trend | crop | stage)`.
- A hit returns a prior diagnosis/plan in **~1 ms** with **zero GPU decode**.
- Target steady-state hit rate: **≥ 40%**, cutting GPU invocations by roughly **38%** in maintenance conditions.
- Invalidation:
  - TTL expiry (default **120 min**)
  - Trend reversal (`> +1.5°C / 15 min` on a stable-maintenance diagnosis)
  - Photoperiod transition (`Lights_ON ↔ OFF`) → full cache flush via `flush_cache`

### 2. Reduce prefill cost (KV-cache planning)

Prefill optimization is described in detail in [Prefill Optimization](#prefill-optimization). In short: the static system prefix is prefilled once per workflow cycle, KV state is snapshotted and restored for later stages, and the semantic cache can bypass prefill entirely when greenhouse conditions repeat.

### 3. Strict serial inference

- Only **one** `infer` executes at a time per server process.
- Prevents concurrent GPU kernels that would spike power and trigger thermal throttling on Orin Nano.
- Workflow LLM calls are already sequential in `LocalWorkflow`; the server enforces the same constraint at the hardware boundary.

### 4. Model lifecycle (inference device)

Production path (`vf-llama`, `--features llama`):

| Phase | Behavior | Power impact |
|-------|----------|----------------|
| Boot | Load Q4_K_M GGUF into unified memory once | One-time ~2.7 GB allocation |
| Warmup | Dummy decode (`"Ready."`) compiles CUDA kernels | Short GPU burst at startup |
| Idle between cycles | Model stays resident; no unload | Low idle power, instant readiness |
| Active cycle | Serial decode per stage; cache hits skip GPU | Bursty, bounded by ~70 s budget |

#### Multi-model registry and OOM fallback

Model selection is driven by [`models.json`](models.json) on both server and client:

| Field | Purpose |
|-------|---------|
| `priority` | Lower number = preferred; defines OOM fallback order |
| `stages` | Workflow stages that default to this model |
| `preload` | Load at server warmup / client connect |
| `oom_fallback_only` | Use only when a larger model OOMs |

**Server behavior:**

1. Resolve model from `stage` + optional `model_name` in the infer request.
2. On CUDA / llama.cpp OOM (or mock OOM in test mode), walk the fallback chain by `priority` and retry with the next smaller model.
3. `InferResponse` includes `model_used`, `model_fallback`, and `oom_recovered` so the client can log degraded runs.
4. Semantic cache keys include `model_name` so a fallback answer does not mask a primary-model cache entry.

**Client behavior (`llm/clients/vf_models.py`):**

1. Maps each workflow stage to the registry default model.
2. Sends `preload_models` hints on each infer (next likely stages).
3. Calls `preload` at connect for models marked `preload: true`.
4. Logs cache hits and OOM fallback from `InferResponse`.

Configure registry path with `VF_MODELS_CONFIG` (default: `inference/models.json`). Simulate OOM in mock mode with `VF_MOCK_OOM_MODELS=qwen2.5-4b-agent-q4km`.

Operational guidance (see [`DEPLOY.md`](DEPLOY.md)):

- Run vf-server under **systemd** so the model is warm before the first control cycle.
- Restrict TCP port **9500** to the business device IP only.
- Monitor `tegrastats` / thermal throttling; reduce `VF_N_GPU_LAYERS` if sustained throttling occurs.
- Use **mock mode** on dev machines to validate protocol and workflow without powering a GPU.

### 5. Business device stays lightweight

- The gateway runs Python orchestration only — no PyTorch, no GGUF, no CUDA.
- This keeps the control host in a low-power state while the Jetson bears inference load.

### 6. Cycle budget awareness

- Proxy reads `VF_CYCLE_BUDGET_SEC` (default **70**) and logs a warning if `LocalWorkflow` exceeds it.
- The 15-minute outer loop retains ~**92% headroom** for retries and rare branches (re-diagnosis, re-plan after simulation failure).

---

## Directory Layout

```
inference/
├── README.md           ← this document
├── DEPLOY.md           ← Jetson production setup (systemd, build flags)
├── proto/
│   └── schema.json     ← TCP message JSON schema
├── server/             ← Rust workspace
│   ├── vf-core/        ← protocol, semantic cache, KV manager, inference service
│   ├── vf-mock/        ← test backend (fixture JSON, no GPU)
│   ├── vf-llama/       ← llama.cpp FFI (`ffi/`, `session/`, `runtime/`, `build.rs`)
│   └── vf-server/      ← TCP server binary
└── client/
    └── vf_proxy/       ← proxy process (CLI + optional local request server)

llm/clients/            ← used by vf-proxy (not duplicated here)
├── vf_tcp.py           ← TCP transport + heartbeat thread
├── vf_server.py        ← BaseLLMClient proxy to vf-server
├── vf_models.py        ← stage→model mapping + preload hints
├── vf_context.py       ← per-cycle workflow session (cycle_id, sensor context)
└── vf_prompt.py        ← prompt split, stage detection, cache signatures
```

---

## Operating Modes

### Test mode (no GPU)

```bash
# Terminal 1 — mock server
cd inference/server
cargo run -p vf-server -- --mode mock --port 9500 \
  --fixtures-dir ../../fixtures/inference

# Terminal 2 — full llm/ workflow via proxy
export LLM_PROVIDER=vf_server VF_SERVER_HOST=127.0.0.1 VF_SERVER_PORT=9500
python -m vf_proxy.cli --input fixtures/esp32_state.json
```

Mock mode uses real cache/KV/serial logic but returns fixed JSON per stage from `fixtures/inference/`. Suitable for CI and protocol development on non-Jetson machines.

### Production mode

```bash
cargo build --release -p vf-server --features llama
# See DEPLOY.md for systemd, model path, firewall
```

---

## Entry Points

| Command | Description |
|---------|-------------|
| `python -m vf_proxy.cli --input <sensor.json>` | One-shot workflow (equivalent to `llm/demo.py` with `vf_server` provider) |
| `python -m vf_proxy.cli --serve --listen-port 9600` | Long-lived proxy accepting `run_workflow` requests |
| `python llm/demo.py --provider vf_server --host <ip> --port 9500` | Same workflow, via existing demo CLI |
| `cargo run -p vf-server -- --mode mock\|llama` | Inference server |

---

## Environment Variables

### Inference server (Jetson)

| Variable | Default | Description |
|----------|---------|-------------|
| `VF_MODE` | `mock` | `mock` or `llama` |
| `VF_MODEL_PATH` | — | GGUF path (llama mode) |
| `VF_MODEL_NAME` | `qwen2.5-4b-agent-q4km` | Default model identifier |
| `VF_MODELS_CONFIG` | `inference/models.json` | Multi-model registry (priority, stages, preload) |
| `VF_MOCK_OOM_MODELS` | `qwen2.5-4b-agent-q4km` | Comma-separated models to simulate OOM (mock mode) |
| `VF_PORT` | `9500` | TCP listen port |
| `VF_CACHE_TTL_MIN` | `120` | Semantic cache TTL |
| `VF_N_GPU_LAYERS` | `99` | llama.cpp GPU layer offload |
| `VF_FIXTURES_DIR` | `fixtures/inference` | Mock backend fixture directory |

### Workflow proxy (business device)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | — | Set to `vf_server` |
| `VF_SERVER_HOST` | `127.0.0.1` | Inference device IP |
| `VF_SERVER_PORT` | `9500` | Inference server port |
| `VF_HEARTBEAT_SEC` | `10` | Heartbeat interval |
| `VF_MODELS_CONFIG` | `inference/models.json` | Client-side stage→model mapping (same file as server) |
| `VF_CYCLE_BUDGET_SEC` | `70` | Per-cycle latency warning threshold |

---

## Further Reading

- [`DEPLOY.md`](DEPLOY.md) — cross-compile, systemd unit, firewall, acceptance targets
- [`proto/schema.json`](proto/schema.json) — full message schema
- [`llm/demo.py`](../llm/demo.py) — reference workflow entry point
