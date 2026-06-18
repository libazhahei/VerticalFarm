use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};

use vf_core::config::ServerConfig;
use vf_core::error::{CoreError, CoreResult};
use vf_core::kv::KvManager;
use vf_core::model_manager::ModelRuntime;
use vf_core::models::ModelRegistry;
use vf_core::protocol::{InferResult, PromptSegments};

use crate::session::{log_system_info, LlamaSession};

static BACKEND_INITIALIZED: AtomicBool = AtomicBool::new(false);

pub struct LlamaRuntime {
    registry: ModelRegistry,
    config: ServerConfig,
    sessions: HashMap<String, LlamaSession>,
    active_model: Option<String>,
}

impl LlamaRuntime {
    pub fn load(config: &ServerConfig, registry: ModelRegistry) -> CoreResult<Self> {
        init_backend_once()?;
        log_system_info();
        Ok(Self {
            registry,
            config: config.clone(),
            sessions: HashMap::new(),
            active_model: None,
        })
    }

    fn resolve_model_path(&self, model_name: &str) -> CoreResult<PathBuf> {
        if let Some(spec) = self.registry.get(model_name) {
            return Ok(PathBuf::from(&spec.path));
        }
        if let Some(path) = &self.config.model_path {
            return Ok(path.clone());
        }
        Err(CoreError::Inference(format!(
            "no GGUF path for model {model_name}; set path in models.json or VF_MODEL_PATH"
        )))
    }

    fn load_session(&mut self, model_name: &str) -> CoreResult<()> {
        if self.sessions.contains_key(model_name) {
            self.active_model = Some(model_name.to_string());
            return Ok(());
        }

        let path = self.resolve_model_path(model_name)?;
        let path_str = path
            .to_str()
            .ok_or_else(|| CoreError::Inference(format!("invalid model path: {}", path.display())))?
            .to_string();

        let n_threads = std::env::var("VF_N_THREADS")
            .ok()
            .and_then(|value| value.parse().ok())
            .unwrap_or(4);

        let mut session = LlamaSession::load(
            model_name,
            &path_str,
            self.config.n_ctx,
            self.config.n_ctx.min(512),
            self.config.n_gpu_layers,
            n_threads,
        )?;
        session.warmup()?;

        self.sessions.insert(model_name.to_string(), session);
        self.active_model = Some(model_name.to_string());
        Ok(())
    }

    fn unload_session(&mut self, model_name: &str) {
        self.sessions.remove(model_name);
        if self.active_model.as_deref() == Some(model_name) {
            self.active_model = self.sessions.keys().next().cloned();
        }
        tracing::warn!(model = %model_name, "llama model unloaded");
    }
}

impl ModelRuntime for LlamaRuntime {
    fn preload(&mut self, model_name: &str) -> CoreResult<()> {
        if self.registry.get(model_name).is_none() {
            return Err(CoreError::Inference(format!("unknown model: {model_name}")));
        }
        self.load_session(model_name)?;
        tracing::info!(model = %model_name, "llama model preloaded");
        Ok(())
    }

    fn unload(&mut self, model_name: &str) {
        self.unload_session(model_name);
    }

    fn infer_on_model(
        &mut self,
        model_name: &str,
        stage: &str,
        cycle_id: &str,
        static_prefix: &str,
        prompt_variable: &str,
        kv: &mut KvManager,
        max_tokens: u32,
        temperature: f32,
    ) -> CoreResult<InferResult> {
        if !self.sessions.contains_key(model_name) {
            self.preload(model_name)?;
        }
        self.active_model = Some(model_name.to_string());

        let prompt = PromptSegments {
            static_prefix: static_prefix.to_string(),
            instruction: String::new(),
            sensor_state: prompt_variable.to_string(),
        };
        let plan = kv.prepare_cycle_stage(cycle_id, &prompt);

        let session = self
            .sessions
            .get_mut(model_name)
            .ok_or_else(|| CoreError::Inference(format!("session missing for {model_name}")))?;

        tracing::debug!(
            model = %model_name,
            stage = %stage,
            cycle_id = %cycle_id,
            restored = plan.restored_from_snapshot,
            "llama infer"
        );

        session.infer(
            cycle_id,
            static_prefix,
            prompt_variable,
            &plan,
            max_tokens,
            temperature,
        )
    }

    fn loaded_models(&self) -> Vec<String> {
        self.sessions.keys().cloned().collect()
    }

    fn active_model(&self) -> Option<String> {
        self.active_model.clone()
    }

    fn simulate_oom(&self, _model_name: &str) -> bool {
        false
    }
}

fn init_backend_once() -> CoreResult<()> {
    if BACKEND_INITIALIZED
        .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
        .is_ok()
    {
        unsafe { crate::ffi::llama_backend_init() };
    }
    Ok(())
}

impl Drop for LlamaRuntime {
    fn drop(&mut self) {
        self.sessions.clear();
        if BACKEND_INITIALIZED.load(Ordering::SeqCst) {
            unsafe { crate::ffi::llama_backend_free() };
            BACKEND_INITIALIZED.store(false, Ordering::SeqCst);
        }
    }
}
