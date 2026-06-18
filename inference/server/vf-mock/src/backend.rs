use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;

use vf_core::config::ServerConfig;
use vf_core::error::{CoreError, CoreResult};
use vf_core::kv::{KvManager, KvStagePlan};
use vf_core::model_manager::ModelRuntime;
use vf_core::models::ModelRegistry;
use vf_core::protocol::{InferMetrics, InferResult, PromptSegments};

pub struct MockRuntime {
    fixtures: HashMap<String, String>,
    prefill_delay: Duration,
    decode_delay: Duration,
    loaded_models: HashSet<String>,
    active_model: Option<String>,
    oom_models: HashSet<String>,
    registry: ModelRegistry,
}

impl MockRuntime {
    fn load_fixtures(dir: &PathBuf) -> CoreResult<HashMap<String, String>> {
        let mut fixtures = HashMap::new();
        if !dir.exists() {
            tracing::warn!(path = %dir.display(), "fixtures directory missing, using built-in defaults");
            return Ok(Self::default_fixtures());
        }

        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) != Some("json") {
                continue;
            }
            let stage = path
                .file_stem()
                .and_then(|name| name.to_str())
                .unwrap_or("unknown")
                .to_string();
            let content = fs::read_to_string(&path)?;
            fixtures.insert(stage, content);
        }

        if fixtures.is_empty() {
            return Ok(Self::default_fixtures());
        }
        Ok(fixtures)
    }

    fn default_fixtures() -> HashMap<String, String> {
        HashMap::from([
            (
                "diagnosis".into(),
                include_str!("../../../../fixtures/inference/diagnosis.json").to_string(),
            ),
            (
                "diagnosis_rethink".into(),
                include_str!("../../../../fixtures/inference/diagnosis_rethink.json").to_string(),
            ),
            (
                "diagnosis_assessment".into(),
                include_str!("../../../../fixtures/inference/diagnosis_assessment.json").to_string(),
            ),
            (
                "action_plan".into(),
                include_str!("../../../../fixtures/inference/action_plan.json").to_string(),
            ),
            (
                "action_assessment".into(),
                include_str!("../../../../fixtures/inference/action_assessment.json").to_string(),
            ),
            (
                "side_effects".into(),
                include_str!("../../../../fixtures/inference/side_effects.json").to_string(),
            ),
            (
                "decision".into(),
                include_str!("../../../../fixtures/inference/decision.json").to_string(),
            ),
            (
                "final_command".into(),
                include_str!("../../../../fixtures/inference/final_command.json").to_string(),
            ),
        ])
    }

    fn lookup_fixture(&self, stage: &str) -> CoreResult<String> {
        self.fixtures
            .get(stage)
            .cloned()
            .ok_or_else(|| CoreError::Inference(format!("no fixture for stage: {stage}")))
    }

    fn simulate_latency(&self, plan: &KvStagePlan, variable: &str, max_tokens: u32) -> InferMetrics {
        let prefill_tokens = plan.estimate_prefill_tokens(variable);
        let decode_tokens = (max_tokens / 8).max(8);
        thread::sleep(self.prefill_delay);
        thread::sleep(self.decode_delay);
        InferMetrics {
            prefill_ms: self.prefill_delay.as_millis() as u64,
            decode_ms: self.decode_delay.as_millis() as u64,
            prefill_tokens,
            decode_tokens,
        }
    }

    pub fn load(config: &ServerConfig, registry: ModelRegistry) -> CoreResult<Self> {
        let fixtures = Self::load_fixtures(&config.fixtures_dir)?;
        Ok(Self {
            fixtures,
            prefill_delay: Duration::from_millis(config.mock_prefill_ms),
            decode_delay: Duration::from_millis(config.mock_decode_ms),
            loaded_models: HashSet::new(),
            active_model: None,
            oom_models: config.mock_simulate_oom_models.iter().cloned().collect(),
            registry,
        })
    }
}

impl ModelRuntime for MockRuntime {
    fn preload(&mut self, model_name: &str) -> CoreResult<()> {
        if self.registry.get(model_name).is_none() {
            return Err(CoreError::Inference(format!("unknown model: {model_name}")));
        }
        self.loaded_models.insert(model_name.to_string());
        self.active_model = Some(model_name.to_string());
        tracing::info!(model = %model_name, "mock model preloaded");
        Ok(())
    }

    fn unload(&mut self, model_name: &str) {
        self.loaded_models.remove(model_name);
        if self.active_model.as_deref() == Some(model_name) {
            self.active_model = self.loaded_models.iter().next().cloned();
        }
        tracing::warn!(model = %model_name, "mock model unloaded after OOM");
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
        _temperature: f32,
    ) -> CoreResult<InferResult> {
        if !self.loaded_models.contains(model_name) {
            self.preload(model_name)?;
        }
        self.active_model = Some(model_name.to_string());

        let prompt = PromptSegments {
            static_prefix: static_prefix.to_string(),
            instruction: String::new(),
            sensor_state: prompt_variable.to_string(),
        };
        let plan = kv.prepare_cycle_stage(cycle_id, &prompt);
        let output = self.lookup_fixture(stage)?;
        let metrics = self.simulate_latency(&plan, prompt_variable, max_tokens);
        tracing::debug!(
            model = %model_name,
            stage = %stage,
            cycle_id = %cycle_id,
            restored = plan.restored_from_snapshot,
            "mock infer"
        );
        Ok(InferResult { output, metrics })
    }

    fn loaded_models(&self) -> Vec<String> {
        self.loaded_models.iter().cloned().collect()
    }

    fn active_model(&self) -> Option<String> {
        self.active_model.clone()
    }

    fn simulate_oom(&self, model_name: &str) -> bool {
        self.oom_models.contains(model_name)
    }
}

// Backward-compatible alias
pub type MockBackend = MockRuntime;
