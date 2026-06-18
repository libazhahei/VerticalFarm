use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::error::{CoreError, CoreResult};

#[derive(Debug, Clone, Deserialize)]
pub struct ModelRegistryFile {
    pub default_model: String,
    #[serde(default = "default_oom_fallback")]
    pub oom_fallback: bool,
    pub models: Vec<ModelSpec>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ModelSpec {
    pub name: String,
    pub path: String,
    pub priority: u32,
    #[serde(default)]
    pub vram_mb: u32,
    #[serde(default)]
    pub stages: Vec<String>,
    #[serde(default)]
    pub preload: bool,
    #[serde(default)]
    pub oom_fallback_only: bool,
}

fn default_oom_fallback() -> bool {
    true
}

#[derive(Debug, Clone)]
pub struct ModelRegistry {
    pub default_model: String,
    pub oom_fallback: bool,
    models: Vec<ModelSpec>,
    by_name: HashMap<String, ModelSpec>,
    by_stage: HashMap<String, String>,
}

impl ModelRegistry {
    pub fn load(path: &Path) -> CoreResult<Self> {
        let content = fs::read_to_string(path)?;
        let file: ModelRegistryFile = serde_json::from_str(&content)?;
        Self::from_file(file)
    }

    pub fn from_file(file: ModelRegistryFile) -> CoreResult<Self> {
        if file.models.is_empty() {
            return Err(CoreError::Inference("model registry is empty".into()));
        }

        let mut by_name = HashMap::new();
        let mut by_stage = HashMap::new();
        let mut fallback_model = file.default_model.clone();

        for spec in &file.models {
            by_name.insert(spec.name.clone(), spec.clone());
            for stage in &spec.stages {
                if stage == "*" {
                    fallback_model = spec.name.clone();
                    continue;
                }
                by_stage.insert(stage.clone(), spec.name.clone());
            }
        }

        if !by_name.contains_key(&file.default_model) {
            return Err(CoreError::Inference(format!(
                "default_model {} not found in registry",
                file.default_model
            )));
        }

        let _ = fallback_model;
        Ok(Self {
            default_model: file.default_model,
            oom_fallback: file.oom_fallback,
            models: file.models,
            by_name,
            by_stage,
        })
    }

    pub fn default_path() -> PathBuf {
        std::env::var("VF_MODELS_CONFIG")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("inference/models.json"))
    }

    pub fn resolve_for_stage(&self, stage: &str, requested: &str) -> String {
        if self.by_name.contains_key(requested) {
            return requested.to_string();
        }
        self.by_stage
            .get(stage)
            .cloned()
            .unwrap_or_else(|| self.default_model.clone())
    }

    pub fn fallback_chain(&self, start_model: &str) -> Vec<ModelSpec> {
        let Some(start) = self.by_name.get(start_model) else {
            return self.models.clone();
        };

        let mut chain: Vec<ModelSpec> = self
            .models
            .iter()
            .filter(|spec| spec.priority >= start.priority)
            .cloned()
            .collect();
        chain.sort_by_key(|spec| spec.priority);
        chain
    }

    pub fn preload_candidates(&self) -> Vec<String> {
        self.models
            .iter()
            .filter(|spec| spec.preload)
            .map(|spec| spec.name.clone())
            .collect()
    }

    pub fn get(&self, name: &str) -> Option<&ModelSpec> {
        self.by_name.get(name)
    }

    pub fn all_names(&self) -> Vec<String> {
        self.models.iter().map(|spec| spec.name.clone()).collect()
    }

    pub fn is_oom_error(message: &str) -> bool {
        let lower = message.to_lowercase();
        lower.contains("out of memory")
            || lower.contains("oom")
            || lower.contains("cuda malloc")
            || lower.contains("failed to allocate")
            || lower.contains("insufficient memory")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_registry() -> ModelRegistry {
        ModelRegistry::from_file(ModelRegistryFile {
            default_model: "large".into(),
            oom_fallback: true,
            models: vec![
                ModelSpec {
                    name: "large".into(),
                    path: "/opt/large.gguf".into(),
                    priority: 1,
                    vram_mb: 2500,
                    stages: vec!["diagnosis".into()],
                    preload: true,
                    oom_fallback_only: false,
                },
                ModelSpec {
                    name: "small".into(),
                    path: "/opt/small.gguf".into(),
                    priority: 2,
                    vram_mb: 900,
                    stages: vec!["*".into()],
                    preload: false,
                    oom_fallback_only: true,
                },
            ],
        })
        .unwrap()
    }

    #[test]
    fn resolve_stage_model() {
        let registry = sample_registry();
        assert_eq!(registry.resolve_for_stage("diagnosis", "unknown"), "large");
    }

    #[test]
    fn fallback_chain_orders_by_priority() {
        let registry = sample_registry();
        let chain = registry.fallback_chain("large");
        assert_eq!(chain.len(), 2);
        assert_eq!(chain[0].name, "large");
        assert_eq!(chain[1].name, "small");
    }
}
