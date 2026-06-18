//! Production `ModelRuntime` backed by llama.cpp.

#[cfg(not(feature = "llama"))]
use vf_core::config::ServerConfig;
#[cfg(not(feature = "llama"))]
use vf_core::error::{CoreError, CoreResult};
#[cfg(not(feature = "llama"))]
use vf_core::model_manager::ModelRuntime;
#[cfg(not(feature = "llama"))]
use vf_core::models::ModelRegistry;

#[cfg(feature = "llama")]
#[path = "runtime/imp.rs"]
mod imp;

#[cfg(feature = "llama")]
pub use imp::LlamaRuntime;

#[cfg(not(feature = "llama"))]
pub struct LlamaRuntime {
    _private: (),
}

#[cfg(not(feature = "llama"))]
impl LlamaRuntime {
    pub fn load(_config: &ServerConfig, _registry: ModelRegistry) -> CoreResult<Self> {
        Err(CoreError::Inference(
            "vf-llama built without `llama` feature; rebuild with --features llama".into(),
        ))
    }
}

#[cfg(not(feature = "llama"))]
impl ModelRuntime for LlamaRuntime {
    fn preload(&mut self, _model_name: &str) -> CoreResult<()> {
        Err(CoreError::Inference(
            "vf-llama built without `llama` feature".into(),
        ))
    }

    fn unload(&mut self, _model_name: &str) {}

    fn infer_on_model(
        &mut self,
        _model_name: &str,
        _stage: &str,
        _cycle_id: &str,
        _static_prefix: &str,
        _prompt_variable: &str,
        _kv: &mut vf_core::kv::KvManager,
        _max_tokens: u32,
        _temperature: f32,
    ) -> CoreResult<vf_core::protocol::InferResult> {
        Err(CoreError::Inference(
            "vf-llama built without `llama` feature".into(),
        ))
    }

    fn loaded_models(&self) -> Vec<String> {
        Vec::new()
    }

    fn active_model(&self) -> Option<String> {
        None
    }

    fn simulate_oom(&self, _model_name: &str) -> bool {
        false
    }
}

/// Backward-compatible alias used by older docs.
pub type LlamaBackend = LlamaRuntime;
