use std::time::Instant;

use crate::cache::{is_stable_maintenance_output, SemanticCache};
use crate::config::ServerConfig;
use crate::error::{CoreError, CoreResult};
use crate::kv::KvManager;
use crate::model_manager::{InferExecution, ModelManager, ModelRuntime};
use crate::protocol::{ClientMessage, InferMetrics, ServerMessage};

pub struct InferenceService<R: ModelRuntime> {
    manager: ModelManager<R>,
    cache: SemanticCache,
    kv: KvManager,
    started_at: Instant,
}

impl<R: ModelRuntime> InferenceService<R> {
    pub fn new(manager: ModelManager<R>, config: &ServerConfig) -> Self {
        Self {
            manager,
            cache: SemanticCache::new(config.cache_ttl),
            kv: KvManager::default(),
            started_at: Instant::now(),
        }
    }

    pub fn model_ready(&self) -> bool {
        self.manager.is_ready()
    }

    pub fn uptime_ms(&self) -> u64 {
        self.started_at.elapsed().as_millis() as u64
    }

    pub fn heartbeat_ack(&self) -> ServerMessage {
        ServerMessage::HeartbeatAck {
            server_uptime_ms: self.uptime_ms(),
            model_ready: self.model_ready(),
            active_model: self.manager.active_model(),
            loaded_models: self.manager.loaded_models(),
            available_models: self.manager.registry().all_names(),
        }
    }

    pub fn handle_preload(&mut self, models: &[String]) -> CoreResult<ServerMessage> {
        let loaded = self.manager.preload_models(models)?;
        Ok(ServerMessage::PreloadAck { loaded_models: loaded })
    }

    pub fn handle_cycle_end(&mut self, cycle_id: &str) -> ServerMessage {
        self.kv.end_cycle(cycle_id);
        ServerMessage::CycleEndAck {
            cycle_id: cycle_id.to_string(),
        }
    }

    pub fn handle_flush_cache(&mut self) -> ServerMessage {
        let cleared = self.cache.flush();
        ServerMessage::FlushCacheAck {
            entries_cleared: cleared,
        }
    }

    pub fn handle_infer(&mut self, message: &ClientMessage) -> CoreResult<ServerMessage> {
        let ClientMessage::Infer {
            request_id,
            cycle_id,
            stage,
            model_name,
            prompt,
            state_signature,
            invalidate_reason,
            max_tokens,
            temperature,
            allow_model_fallback,
            preload_models,
            ..
        } = message
        else {
            return Err(CoreError::Inference("expected infer".into()));
        };

        if !preload_models.is_empty() {
            let _ = self.manager.preload_models(preload_models);
        }

        let resolved_model = self
            .manager
            .registry()
            .resolve_for_stage(stage, model_name);

        if let Some(hit) = self.cache.lookup(
            stage,
            &resolved_model,
            state_signature,
            invalidate_reason.as_deref(),
        )? {
            tracing::info!(request_id = %request_id, stage = %stage, model = %resolved_model, "semantic cache hit");
            return Ok(ServerMessage::InferResponse {
                request_id: request_id.clone(),
                cache_hit: true,
                output: hit,
                metrics: Some(InferMetrics {
                    prefill_ms: 0,
                    decode_ms: 1,
                    prefill_tokens: 0,
                    decode_tokens: 0,
                }),
                model_used: Some(resolved_model),
                model_fallback: false,
                oom_recovered: false,
            });
        }

        let plan = self.kv.prepare_cycle_stage(cycle_id, prompt);
        tracing::debug!(
            cycle_id = %cycle_id,
            stage = %stage,
            model = %model_name,
            prefill_static = plan.prefill_static,
            restored = plan.restored_from_snapshot,
            "kv plan prepared"
        );

        let InferExecution {
            result,
            model_used,
            model_fallback,
            oom_recovered,
        } = self.manager.infer_with_policy(
            model_name,
            stage,
            cycle_id,
            &prompt.static_prefix,
            &prompt.variable_text(),
            &mut self.kv,
            *max_tokens,
            *temperature,
            *allow_model_fallback,
        )?;

        tracing::info!(
            request_id = %request_id,
            stage = %stage,
            model_used = %model_used,
            model_fallback = model_fallback,
            oom_recovered = oom_recovered,
            prefill_ms = result.metrics.prefill_ms,
            decode_ms = result.metrics.decode_ms,
            "inference complete"
        );

        let diagnosis_stable =
            stage == "diagnosis" && is_stable_maintenance_output(&result.output);
        let key = SemanticCache::cache_key(stage, &model_used, state_signature);
        self.cache
            .insert(key, result.output.clone(), diagnosis_stable);

        Ok(ServerMessage::InferResponse {
            request_id: request_id.clone(),
            cache_hit: false,
            output: result.output,
            metrics: Some(result.metrics),
            model_used: Some(model_used),
            model_fallback,
            oom_recovered,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::{ServerConfig, ServerMode};
    use crate::model_manager::ModelRuntime;
    use crate::models::{ModelRegistry, ModelRegistryFile, ModelSpec};
    use crate::protocol::{PromptSegments, StateSignature};
    use crate::kv::KvManager;
    use crate::protocol::InferResult;

    struct StubRuntime;

    impl ModelRuntime for StubRuntime {
        fn preload(&mut self, _model_name: &str) -> CoreResult<()> {
            Ok(())
        }

        fn unload(&mut self, _model_name: &str) {}

        fn infer_on_model(
            &mut self,
            _model_name: &str,
            _stage: &str,
            _cycle_id: &str,
            _static: &str,
            _variable: &str,
            _kv: &mut KvManager,
            _max_tokens: u32,
            _temperature: f32,
        ) -> CoreResult<InferResult> {
            Ok(InferResult {
                output: r#"{"states":["Stable Maintenance"],"confidence":[10]}"#.into(),
                metrics: InferMetrics {
                    prefill_ms: 1,
                    decode_ms: 1,
                    prefill_tokens: 10,
                    decode_tokens: 5,
                },
            })
        }

        fn loaded_models(&self) -> Vec<String> {
            vec!["test".into()]
        }

        fn active_model(&self) -> Option<String> {
            Some("test".into())
        }

        fn simulate_oom(&self, _model_name: &str) -> bool {
            false
        }
    }

    fn test_registry() -> ModelRegistry {
        ModelRegistry::from_file(ModelRegistryFile {
            default_model: "test".into(),
            oom_fallback: true,
            models: vec![ModelSpec {
                name: "test".into(),
                path: "/tmp/test.gguf".into(),
                priority: 1,
                vram_mb: 100,
                stages: vec!["diagnosis".into()],
                preload: true,
                oom_fallback_only: false,
            }],
        })
        .unwrap()
    }

    fn test_config() -> ServerConfig {
        ServerConfig {
            mode: ServerMode::Mock,
            port: 9500,
            model_path: None,
            model_name: "test".into(),
            fixtures_dir: "fixtures/inference".into(),
            cache_ttl: std::time::Duration::from_secs(3600),
            mock_prefill_ms: 1,
            mock_decode_ms: 1,
            n_ctx: 4096,
            n_gpu_layers: 0,
            models_config: "inference/models.json".into(),
            mock_simulate_oom_models: vec![],
        }
    }

    #[test]
    fn infer_miss_then_hit() {
        let manager = ModelManager::new(test_registry(), StubRuntime);
        let mut service = InferenceService::new(manager, &test_config());
        let sig = StateSignature {
            internal_temp_bucket: "18-20".into(),
            external_temp_bucket: "15-18".into(),
            humidity_bucket: "60-70".into(),
            photoperiod: "ON".into(),
            temp_trend_sign: "+".into(),
            temp_trend_magnitude: "lo".into(),
            crop: "iceberg_lettuce".into(),
            growth_stage: "head_development".into(),
            temp_trend_c_per_15min: Some(0.2),
        };
        let prompt = PromptSegments {
            static_prefix: "sys".into(),
            instruction: "diag".into(),
            sensor_state: "19C".into(),
        };
        let msg = ClientMessage::Infer {
            request_id: "r1".into(),
            cycle_id: "c1".into(),
            stage: "diagnosis".into(),
            model_name: "test".into(),
            prompt,
            state_signature: sig,
            max_tokens: 128,
            temperature: 0.2,
            invalidate_reason: None,
            allow_model_fallback: true,
            preload_models: vec![],
        };

        let first = service.handle_infer(&msg).unwrap();
        let ServerMessage::InferResponse { cache_hit, .. } = first else {
            panic!("expected infer response");
        };
        assert!(!cache_hit);

        let second = service.handle_infer(&msg).unwrap();
        let ServerMessage::InferResponse { cache_hit, .. } = second else {
            panic!("expected infer response");
        };
        assert!(cache_hit);
    }
}
