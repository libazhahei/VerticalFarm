use std::collections::HashMap;

use crate::protocol::PromptSegments;

#[derive(Debug, Default)]
pub struct KvCycleState {
    pub static_prefilled: bool,
    pub static_token_count: usize,
    pub restore_count: usize,
}

#[derive(Debug, Default)]
pub struct KvManager {
    cycles: HashMap<String, KvCycleState>,
}

impl KvManager {
    pub fn prepare_cycle_stage(
        &mut self,
        cycle_id: &str,
        prompt: &PromptSegments,
    ) -> KvStagePlan {
        let state = self.cycles.entry(cycle_id.to_string()).or_default();
        let static_tokens = prompt.estimate_static_tokens();

        if !state.static_prefilled {
            state.static_prefilled = true;
            state.static_token_count = static_tokens;
            KvStagePlan {
                prefill_static: true,
                prefill_variable: true,
                static_token_count: static_tokens,
                restored_from_snapshot: false,
            }
        } else {
            state.restore_count += 1;
            KvStagePlan {
                prefill_static: false,
                prefill_variable: true,
                static_token_count: state.static_token_count,
                restored_from_snapshot: true,
            }
        }
    }

    pub fn end_cycle(&mut self, cycle_id: &str) {
        self.cycles.remove(cycle_id);
    }

    pub fn cycle_count(&self) -> usize {
        self.cycles.len()
    }
}

#[derive(Debug, Clone)]
pub struct KvStagePlan {
    pub prefill_static: bool,
    pub prefill_variable: bool,
    pub static_token_count: usize,
    pub restored_from_snapshot: bool,
}

impl KvStagePlan {
    pub fn estimate_prefill_tokens(&self, variable_text: &str) -> u32 {
        let variable_tokens = (variable_text.len() / 4).max(1) as u32;
        if self.prefill_static {
            self.static_token_count as u32 + variable_tokens
        } else {
            variable_tokens
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn second_stage_restores_kv() {
        let mut kv = KvManager::default();
        let prompt = PromptSegments {
            static_prefix: "system".repeat(80),
            instruction: "diagnose".into(),
            sensor_state: "temp 19".into(),
        };
        let first = kv.prepare_cycle_stage("cycle-1", &prompt);
        assert!(first.prefill_static);
        assert!(!first.restored_from_snapshot);

        let second = kv.prepare_cycle_stage("cycle-1", &prompt);
        assert!(!second.prefill_static);
        assert!(second.restored_from_snapshot);
    }
}
