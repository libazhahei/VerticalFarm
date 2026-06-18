use std::collections::HashMap;
use std::time::{Duration, Instant};

use sha2::{Digest, Sha256};

use crate::error::CoreResult;
use crate::protocol::StateSignature;

#[derive(Debug, Clone)]
struct CachedEntry {
    output: String,
    created_at: Instant,
    ttl: Duration,
    diagnosis_stable: bool,
}

#[derive(Debug, Default)]
pub struct SemanticCache {
    entries: HashMap<String, CachedEntry>,
    ttl: Duration,
    last_photoperiod: Option<String>,
}

impl SemanticCache {
    pub fn new(ttl: Duration) -> Self {
        Self {
            entries: HashMap::new(),
            ttl,
            last_photoperiod: None,
        }
    }

    pub fn cache_key(stage: &str, model_name: &str, signature: &StateSignature) -> String {
        let raw = format!(
            "{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
            stage,
            model_name,
            signature.internal_temp_bucket,
            signature.external_temp_bucket,
            signature.humidity_bucket,
            signature.photoperiod,
            signature.temp_trend_sign,
            signature.temp_trend_magnitude,
            signature.crop,
            signature.growth_stage,
        );
        let digest = Sha256::digest(raw.as_bytes());
        format!("{:x}", digest)
    }

    pub fn check_photoperiod_transition(&mut self, photoperiod: &str) -> bool {
        let changed = self
            .last_photoperiod
            .as_ref()
            .is_some_and(|prev| prev != photoperiod);
        self.last_photoperiod = Some(photoperiod.to_string());
        if changed {
            self.flush();
            return true;
        }
        false
    }

    pub fn get(&self, key: &str) -> Option<String> {
        let entry = self.entries.get(key)?;
        if entry.created_at.elapsed() > entry.ttl {
            return None;
        }
        Some(entry.output.clone())
    }

    pub fn should_invalidate_for_trend(&self, key: &str, trend_c_per_15min: Option<f64>) -> bool {
        let Some(entry) = self.entries.get(key) else {
            return false;
        };
        if !entry.diagnosis_stable {
            return false;
        }
        trend_c_per_15min.is_some_and(|trend| trend > 1.5)
    }

    pub fn insert(&mut self, key: String, output: String, diagnosis_stable: bool) {
        self.entries.insert(
            key,
            CachedEntry {
                output,
                created_at: Instant::now(),
                ttl: self.ttl,
                diagnosis_stable,
            },
        );
    }

    pub fn flush(&mut self) -> usize {
        let count = self.entries.len();
        self.entries.clear();
        count
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn lookup(
        &mut self,
        stage: &str,
        model_name: &str,
        signature: &StateSignature,
        invalidate_reason: Option<&str>,
    ) -> CoreResult<Option<String>> {
        if invalidate_reason.is_some() {
            return Ok(None);
        }

        self.check_photoperiod_transition(&signature.photoperiod);
        self.evict_expired();

        let key = Self::cache_key(stage, model_name, signature);
        if self.should_invalidate_for_trend(&key, signature.temp_trend_c_per_15min) {
            self.entries.remove(&key);
            return Ok(None);
        }

        Ok(self.get(&key))
    }

    fn evict_expired(&mut self) {
        self.entries
            .retain(|_, entry| entry.created_at.elapsed() <= entry.ttl);
    }
}

pub fn is_stable_maintenance_output(output: &str) -> bool {
    output.contains("Stable Maintenance") || output.contains("stable maintenance")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_signature() -> StateSignature {
        StateSignature {
            internal_temp_bucket: "18-20".into(),
            external_temp_bucket: "15-18".into(),
            humidity_bucket: "60-70".into(),
            photoperiod: "ON".into(),
            temp_trend_sign: "+".into(),
            temp_trend_magnitude: "lo".into(),
            crop: "iceberg_lettuce".into(),
            growth_stage: "head_development".into(),
            temp_trend_c_per_15min: Some(0.3),
        }
    }

    #[test]
    fn cache_hit_after_insert() {
        let mut cache = SemanticCache::new(Duration::from_secs(3600));
        let sig = sample_signature();
        let key = SemanticCache::cache_key("diagnosis", "test-model", &sig);
        cache.insert(key, r#"{"states":["Stable Maintenance"]}"#.into(), true);
        let result = cache.lookup("diagnosis", "test-model", &sig, None).unwrap();
        assert!(result.is_some());
    }

    #[test]
    fn photoperiod_flush_clears_cache() {
        let mut cache = SemanticCache::new(Duration::from_secs(3600));
        let mut sig = sample_signature();
        let key = SemanticCache::cache_key("diagnosis", "test-model", &sig);
        cache.insert(key, "cached".into(), false);
        cache.check_photoperiod_transition("ON");
        assert_eq!(cache.len(), 1);

        sig.photoperiod = "OFF".into();
        cache.check_photoperiod_transition("OFF");
        assert_eq!(cache.len(), 0);
    }
}
