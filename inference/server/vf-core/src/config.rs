use std::path::PathBuf;
use std::time::Duration;

use crate::models::ModelRegistry;

#[derive(Debug, Clone)]
pub struct ServerConfig {
    pub mode: ServerMode,
    pub port: u16,
    pub model_path: Option<PathBuf>,
    pub model_name: String,
    pub fixtures_dir: PathBuf,
    pub cache_ttl: Duration,
    pub mock_prefill_ms: u64,
    pub mock_decode_ms: u64,
    pub n_ctx: u32,
    pub n_gpu_layers: i32,
    pub models_config: PathBuf,
    pub mock_simulate_oom_models: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ServerMode {
    Mock,
    Llama,
}

impl ServerConfig {
    pub fn from_env() -> Self {
        let mode = match std::env::var("VF_MODE")
            .unwrap_or_else(|_| "mock".into())
            .to_lowercase()
            .as_str()
        {
            "llama" => ServerMode::Llama,
            _ => ServerMode::Mock,
        };

        Self {
            mode,
            port: std::env::var("VF_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(9500),
            model_path: std::env::var("VF_MODEL_PATH").ok().map(PathBuf::from),
            model_name: std::env::var("VF_MODEL_NAME")
                .unwrap_or_else(|_| "qwen2.5-4b-agent-q4km".into()),
            fixtures_dir: std::env::var("VF_FIXTURES_DIR")
                .map(PathBuf::from)
                .unwrap_or_else(|_| PathBuf::from("fixtures/inference")),
            cache_ttl: Duration::from_secs(
                std::env::var("VF_CACHE_TTL_MIN")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(120)
                    * 60,
            ),
            mock_prefill_ms: std::env::var("MOCK_PREFILL_MS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5),
            mock_decode_ms: std::env::var("MOCK_DECODE_MS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5),
            n_ctx: std::env::var("VF_N_CTX")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(4096),
            n_gpu_layers: std::env::var("VF_N_GPU_LAYERS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(99),
            models_config: ModelRegistry::default_path(),
            mock_simulate_oom_models: std::env::var("VF_MOCK_OOM_MODELS")
                .unwrap_or_else(|_| "qwen2.5-4b-agent-q4km".into())
                .split(',')
                .map(|item| item.trim().to_string())
                .filter(|item| !item.is_empty())
                .collect(),
        }
    }
}
