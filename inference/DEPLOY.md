# VerticalFarm Inference Server — Jetson Deployment

Deploy the Rust TCP inference server on a dedicated edge GPU device (e.g. Jetson Orin Nano). Run the Python client on the business device (gateway / control host).

## Build (inference device)

```bash
cd inference/server
cargo build --release -p vf-server --features llama
```

For development / CI without GPU:

```bash
cargo build --release -p vf-server --features mock
```

## Model

Place the trained GGUF artifact on the inference device:

```text
/opt/models/qwen2.5-4b-agent-q4km.gguf
```

Set environment:

```bash
export VF_MODE=llama
export VF_MODEL_PATH=/opt/models/qwen2.5-4b-agent-q4km.gguf
export VF_MODEL_NAME=qwen2.5-4b-agent-q4km
export VF_PORT=9500
```

## systemd unit

Create `/etc/systemd/system/vf-inference-server.service`:

```ini
[Unit]
Description=VerticalFarm Inference TCP Server
After=network.target

[Service]
Type=simple
User=vf
Environment=VF_MODE=llama
Environment=VF_MODEL_PATH=/opt/models/qwen2.5-4b-agent-q4km.gguf
Environment=VF_MODEL_NAME=qwen2.5-4b-agent-q4km
Environment=VF_PORT=9500
Environment=VF_CACHE_TTL_MIN=120
ExecStart=/opt/vf/bin/vf-server --mode llama --port 9500
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vf-inference-server
sudo systemctl start vf-inference-server
```

## Firewall

Allow TCP 9500 only from the business device IP:

```bash
sudo ufw allow from <BUSINESS_DEVICE_IP> to any port 9500 proto tcp
```

## Python client (business device)

The client is a **proxy process** that runs `llm/LocalWorkflow` and sends infer requests to vf-server.

```bash
cd /home/shilong/VerticalFarm
export LLM_PROVIDER=vf_server
export VF_SERVER_HOST=<INFERENCE_DEVICE_IP>
export VF_SERVER_PORT=9500
python -m vf_proxy.cli --input fixtures/esp32_state.json
```

Or run as a request server:

```bash
python -m vf_proxy.cli --serve --listen-port 9600
```

## Local test mode (no GPU)

Terminal 1:

```bash
cd inference/server
cargo run -p vf-server -- --mode mock --port 9500 \
  --fixtures-dir ../../fixtures/inference
```

Terminal 2:

```bash
cd inference/client
pip install -e '.[dev]'
export VF_SERVER_HOST=127.0.0.1
export VF_SERVER_PORT=9500
export LLM_PROVIDER=vf_server
python -m vf_proxy.cli --input fixtures/esp32_state.json
```

## Acceptance targets

| Scenario | Target |
|----------|--------|
| Stable-state cache hit cycle | < 10s |
| Full miss path on Jetson | <= 68s |
| Semantic cache hit rate (steady env) | >= 40% |

## llama.cpp build & link

`vf-llama` links a **prebuilt** CUDA-enabled llama.cpp.

```bash
# On Jetson or cross sysroot
git clone https://github.com/ggerganov/llama.cpp /opt/llama.cpp
cd /opt/llama.cpp
cmake -B build -DGGML_CUDA=ON -DLLAMA_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=OFF
cmake --build build -j"$(nproc)"

export LLAMA_CPP_DIR=/opt/llama.cpp
export LLAMA_LIB_DIR=/opt/llama.cpp/build
export LLAMA_INCLUDE_DIR=/opt/llama.cpp/include
export VF_LLAMA_CUDA=1

cd inference/server
cargo build --release -p vf-server --features llama
```

Cross-compile example (host → aarch64):

```bash
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
export LLAMA_LIB_DIR=/path/to/jetson-sysroot/opt/llama.cpp/build
export LLAMA_INCLUDE_DIR=/path/to/jetson-sysroot/opt/llama.cpp/include
cargo build --release -p vf-server --features llama --target aarch64-unknown-linux-gnu
```

See `vf-llama/cross.example.toml` and `vf-llama/build.rs` for all link-time environment variables.

`VF_MODELS_CONFIG` should list every GGUF (`path` per model). Set `VF_N_GPU_LAYERS`, `VF_N_CTX`, and optional `VF_N_THREADS` at runtime.
