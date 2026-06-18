use std::collections::HashSet;

use tracing::{info, warn};

use crate::error::{CoreError, CoreResult};
use crate::kv::KvManager;
use crate::models::ModelRegistry;
use crate::protocol::InferResult;

pub trait ModelRuntime: Send {
    fn preload(&mut self, model_name: &str) -> CoreResult<()>;
    fn unload(&mut self, model_name: &str);
    fn infer_on_model(
        &mut self,
        model_name: &str,
        stage: &str,
        cycle_id: &str,
        prompt_static: &str,
        prompt_variable: &str,
        kv: &mut KvManager,
        max_tokens: u32,
        temperature: f32,
    ) -> CoreResult<InferResult>;
    fn loaded_models(&self) -> Vec<String>;
    fn active_model(&self) -> Option<String>;
    fn simulate_oom(&self, model_name: &str) -> bool;
}

pub struct InferExecution {
    pub result: InferResult,
    pub model_used: String,
    pub model_fallback: bool,
    pub oom_recovered: bool,
}

pub struct ModelManager<R: ModelRuntime> {
    registry: ModelRegistry,
    runtime: R,
}

impl<R: ModelRuntime> ModelManager<R> {
    pub fn new(registry: ModelRegistry, runtime: R) -> Self {
        Self { registry, runtime }
    }

    pub fn registry(&self) -> &ModelRegistry {
        &self.registry
    }

    pub fn runtime_mut(&mut self) -> &mut R {
        &mut self.runtime
    }

    pub fn is_ready(&self) -> bool {
        !self.runtime.loaded_models().is_empty()
    }

    pub fn loaded_models(&self) -> Vec<String> {
        self.runtime.loaded_models()
    }

    pub fn active_model(&self) -> Option<String> {
        self.runtime.active_model()
    }

    pub fn warmup(&mut self) -> CoreResult<()> {
        for model in self.registry.preload_candidates() {
            if let Err(error) = self.runtime.preload(&model) {
                warn!(model = %model, %error, "preload failed during warmup");
            }
        }
        if self.runtime.loaded_models().is_empty() {
            let default = self.registry.default_model.clone();
            self.runtime.preload(&default)?;
        }
        Ok(())
    }

    pub fn preload_models(&mut self, models: &[String]) -> CoreResult<Vec<String>> {
        let mut loaded = Vec::new();
        for model in models {
            if self.registry.get(model).is_none() {
                continue;
            }
            self.runtime.preload(model)?;
            loaded.push(model.clone());
        }
        Ok(loaded)
    }

    pub fn infer_with_policy(
        &mut self,
        requested_model: &str,
        stage: &str,
        cycle_id: &str,
        prompt_static: &str,
        prompt_variable: &str,
        kv: &mut KvManager,
        max_tokens: u32,
        temperature: f32,
        allow_fallback: bool,
    ) -> CoreResult<InferExecution> {
        let primary = self.registry.resolve_for_stage(stage, requested_model);
        let chain = if allow_fallback && self.registry.oom_fallback {
            self.registry.fallback_chain(&primary)
        } else {
            vec![self.registry.get(&primary).cloned().ok_or_else(|| {
                CoreError::Inference(format!("unknown model: {primary}"))
            })?]
        };

        let mut attempted: HashSet<String> = HashSet::new();
        let mut last_error: Option<CoreError> = None;
        let mut fallback_used = false;
        let mut oom_recovered = false;

        for (index, spec) in chain.iter().enumerate() {
            if !attempted.insert(spec.name.clone()) {
                continue;
            }

            if let Err(error) = self.runtime.preload(&spec.name) {
                last_error = Some(error);
                continue;
            }

            if self.runtime.simulate_oom(&spec.name) {
                oom_recovered = true;
                last_error = Some(CoreError::Inference("out of memory".into()));
                warn!(model = %spec.name, stage = %stage, "simulated OOM, trying fallback model");
                fallback_used = index > 0;
                continue;
            }

            match self.runtime.infer_on_model(
                &spec.name,
                stage,
                cycle_id,
                prompt_static,
                prompt_variable,
                kv,
                max_tokens,
                temperature,
            ) {
                Ok(result) => {
                    if index > 0 {
                        fallback_used = true;
                        info!(
                            model = %spec.name,
                            stage = %stage,
                            "OOM fallback succeeded"
                        );
                    }
                    return Ok(InferExecution {
                        result,
                        model_used: spec.name.clone(),
                        model_fallback: fallback_used,
                        oom_recovered: oom_recovered || fallback_used,
                    });
                }
                Err(error) => {
                    if ModelRegistry::is_oom_error(&error.to_string()) {
                        oom_recovered = true;
                        warn!(model = %spec.name, stage = %stage, %error, "OOM during infer, trying fallback");
                        last_error = Some(error);
                        fallback_used = true;
                        self.runtime.unload(&spec.name);
                        continue;
                    }
                    return Err(error);
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            CoreError::Inference("all models in fallback chain failed".into())
        }))
    }
}
