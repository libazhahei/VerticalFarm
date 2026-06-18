mod frame;
mod queue;

use std::path::PathBuf;
use std::sync::Arc;

use clap::Parser;
use tokio::sync::Mutex;
use tracing_subscriber::EnvFilter;
use vf_core::config::{ServerConfig, ServerMode};
use vf_core::error::CoreResult;
use vf_core::model_manager::ModelManager;
use vf_core::models::ModelRegistry;
use vf_core::service::InferenceService;

#[derive(Parser, Debug)]
#[command(name = "vf-server", about = "VerticalFarm inference TCP server")]
struct Args {
    #[arg(long, env = "VF_MODE", default_value = "mock")]
    mode: String,

    #[arg(long, env = "VF_PORT", default_value_t = 9500)]
    port: u16,

    #[arg(long, env = "VF_MODEL_PATH")]
    model_path: Option<PathBuf>,

    #[arg(long, env = "VF_MODEL_NAME", default_value = "qwen2.5-4b-agent-q4km")]
    model_name: String,

    #[arg(long, env = "VF_MODELS_CONFIG", default_value = "../models.json")]
    models_config: PathBuf,

    #[arg(long, env = "VF_FIXTURES_DIR", default_value = "../../fixtures/inference")]
    fixtures_dir: PathBuf,

    #[arg(long, env = "VF_CACHE_TTL_MIN", default_value_t = 120)]
    cache_ttl_min: u64,

    #[arg(long, env = "MOCK_PREFILL_MS", default_value_t = 5)]
    mock_prefill_ms: u64,

    #[arg(long, env = "MOCK_DECODE_MS", default_value_t = 5)]
    mock_decode_ms: u64,

    #[arg(long, env = "VF_MOCK_OOM_MODELS", default_value = "qwen2.5-4b-agent-q4km")]
    mock_oom_models: String,
}

#[tokio::main]
async fn main() -> CoreResult<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("vf_server=info".parse().unwrap()))
        .init();

    let args = Args::parse();
    let mode = match args.mode.to_lowercase().as_str() {
        "llama" => ServerMode::Llama,
        _ => ServerMode::Mock,
    };

    let config = ServerConfig {
        mode,
        port: args.port,
        model_path: args.model_path,
        model_name: args.model_name,
        fixtures_dir: args.fixtures_dir,
        cache_ttl: std::time::Duration::from_secs(args.cache_ttl_min * 60),
        mock_prefill_ms: args.mock_prefill_ms,
        mock_decode_ms: args.mock_decode_ms,
        n_ctx: 4096,
        n_gpu_layers: 99,
        models_config: args.models_config,
        mock_simulate_oom_models: args
            .mock_oom_models
            .split(',')
            .map(|item| item.trim().to_string())
            .filter(|item| !item.is_empty())
            .collect(),
    };

    run_server(config).await
}

async fn run_server(config: ServerConfig) -> CoreResult<()> {
    let registry = ModelRegistry::load(&config.models_config)?;

    match config.mode {
        ServerMode::Mock => {
            #[cfg(feature = "mock")]
            {
                use vf_mock::MockRuntime;

                let runtime = MockRuntime::load(&config, registry.clone())?;
                let mut manager = ModelManager::new(registry, runtime);
                manager.warmup()?;
                let service = Arc::new(Mutex::new(InferenceService::new(manager, &config)));
                queue::run_tcp_server(config.port, service).await
            }
            #[cfg(not(feature = "mock"))]
            {
                Err(vf_core::error::CoreError::Inference(
                    "mock feature disabled".into(),
                ))
            }
        }
        ServerMode::Llama => {
            #[cfg(feature = "llama")]
            {
                use vf_llama::LlamaRuntime;

                let runtime = LlamaRuntime::load(&config, registry.clone())?;
                let mut manager = ModelManager::new(registry, runtime);
                manager.warmup()?;
                let service = Arc::new(Mutex::new(InferenceService::new(manager, &config)));
                queue::run_tcp_server(config.port, service).await
            }
            #[cfg(not(feature = "llama"))]
            {
                Err(vf_core::error::CoreError::Inference(
                    "llama mode requires building with --features llama".into(),
                ))
            }
        }
    }
}
