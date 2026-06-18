
## Project Structure

- `main.py`, `backend_main.py`, `env_observer.py`: top-level Python entry points for backend/runtime flow.
- `route/`: API route handlers (AI, control, history, plant, utilities).
- `gateway/`: device/messaging integration layer (MQTT/BLE-style pub/sub, service wiring).
- `control/`: control logic and scheduling (`light_schedule.py`, LLM-call coordination, control models).
- `data/`: config + data table definitions, plus generated training data folders.
- `llm/`: core LLM system (clients, workflow stages, prompt templates, output models, demo).
- `inference/`: split edge inference stack (Python proxy + Rust TCP model server).
- `frontend/`: React app (Create React App structure: `src/`, `public/`, npm scripts).
- `fixtures/`: test/sample input fixtures (including inference fixtures).
- `.github/workflows/`: CI automation definitions.

---

## README Files Under Folders (Detailed)

### `inference/README.md` (complete architecture doc)
This README is the clearest technical guide in the repo. It explains:

- Two-machine architecture:
  - **Business device** runs workflow/proxy.
  - **Inference device** runs Rust model server.
- End-to-end control-cycle flow and per-stage LLM call path.
- Performance strategy:
  - semantic cache,
  - prompt splitting,
  - per-cycle KV reuse,
  - strict serial inference.
- TCP protocol (`heartbeat`, `infer`, `flush_cache`, `cycle_end`, etc.).
- Deployment/runtime details and environment variables.
- Directory breakdown inside `inference/`:

### `frontend/README.md`
Standard Create React App README:

- how to run (`npm start`);
- local dev URL (`localhost:3000`);
- note about required Google Maps API key.

This is mostly boilerplate, not project-specific architecture documentation.

### `llm/README.md`
This file contains:

- large prompt templates for multi-step cloud/local LLM flows;
- Pydantic schemas for structured outputs;
- legacy/local prompt blocks and JSON repair prompts.

### `llm/training/README.md`
Doc for model training pipeline:

- full pipeline: synthesize -> augment -> SFT -> DPO -> GGUF export;
- unified config usage (`training_config.json`);
- command-by-command CLI;
- output files and dataset formats;
- relation between training data and inference schemas/prompts.

