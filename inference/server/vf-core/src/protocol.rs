use serde::{Deserialize, Serialize};

use crate::error::{CoreError, CoreResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMessage {
    Heartbeat {
        client_id: String,
        timestamp: String,
    },
    Infer {
        request_id: String,
        cycle_id: String,
        stage: String,
        model_name: String,
        prompt: PromptSegments,
        state_signature: StateSignature,
        #[serde(default = "default_max_tokens")]
        max_tokens: u32,
        #[serde(default = "default_temperature")]
        temperature: f32,
        #[serde(skip_serializing_if = "Option::is_none")]
        invalidate_reason: Option<String>,
        #[serde(default = "default_true")]
        allow_model_fallback: bool,
        #[serde(default, skip_serializing_if = "Vec::is_empty")]
        preload_models: Vec<String>,
    },
    FlushCache {
        reason: String,
    },
    CycleEnd {
        cycle_id: String,
    },
    Preload {
        models: Vec<String>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMessage {
    HeartbeatAck {
        server_uptime_ms: u64,
        model_ready: bool,
        #[serde(skip_serializing_if = "Option::is_none")]
        active_model: Option<String>,
        #[serde(default, skip_serializing_if = "Vec::is_empty")]
        loaded_models: Vec<String>,
        #[serde(default, skip_serializing_if = "Vec::is_empty")]
        available_models: Vec<String>,
    },
    InferResponse {
        request_id: String,
        cache_hit: bool,
        output: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        metrics: Option<InferMetrics>,
        #[serde(skip_serializing_if = "Option::is_none")]
        model_used: Option<String>,
        #[serde(default, skip_serializing_if = "is_false")]
        model_fallback: bool,
        #[serde(default, skip_serializing_if = "is_false")]
        oom_recovered: bool,
    },
    PreloadAck {
        loaded_models: Vec<String>,
    },
    FlushCacheAck {
        entries_cleared: usize,
    },
    CycleEndAck {
        cycle_id: String,
    },
    Error {
        code: String,
        message: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        request_id: Option<String>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptSegments {
    pub static_prefix: String,
    pub instruction: String,
    pub sensor_state: String,
}

impl PromptSegments {
    pub fn full_text(&self) -> String {
        format!(
            "{}\n{}\n{}",
            self.static_prefix, self.instruction, self.sensor_state
        )
    }

    pub fn variable_text(&self) -> String {
        format!("{}\n{}", self.instruction, self.sensor_state)
    }

    pub fn estimate_static_tokens(&self) -> usize {
        (self.static_prefix.len() / 4).max(1)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSignature {
    pub internal_temp_bucket: String,
    pub external_temp_bucket: String,
    pub humidity_bucket: String,
    pub photoperiod: String,
    pub temp_trend_sign: String,
    pub temp_trend_magnitude: String,
    pub crop: String,
    pub growth_stage: String,
    #[serde(default)]
    pub temp_trend_c_per_15min: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct InferMetrics {
    pub prefill_ms: u64,
    pub decode_ms: u64,
    pub prefill_tokens: u32,
    pub decode_tokens: u32,
}

#[derive(Debug, Clone)]
pub struct InferResult {
    pub output: String,
    pub metrics: InferMetrics,
}

fn default_true() -> bool {
    true
}

fn is_false(value: &bool) -> bool {
    !*value
}

fn default_max_tokens() -> u32 {
    256
}

fn default_temperature() -> f32 {
    0.2
}

pub fn encode_message<T: Serialize>(message: &T) -> CoreResult<Vec<u8>> {
    let body = serde_json::to_vec(message)?;
    if body.len() > u32::MAX as usize {
        return Err(CoreError::Protocol("message too large".into()));
    }
    let mut frame = Vec::with_capacity(4 + body.len());
    frame.extend_from_slice(&(body.len() as u32).to_be_bytes());
    frame.extend_from_slice(&body);
    Ok(frame)
}

pub fn decode_client_message(frame: &[u8]) -> CoreResult<ClientMessage> {
    serde_json::from_slice(frame).map_err(|error| CoreError::Protocol(error.to_string()))
}

pub fn decode_server_message(frame: &[u8]) -> CoreResult<ServerMessage> {
    serde_json::from_slice(frame).map_err(|error| CoreError::Protocol(error.to_string()))
}
