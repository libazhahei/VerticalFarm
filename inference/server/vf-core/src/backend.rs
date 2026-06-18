use crate::config::ServerConfig;
use crate::error::CoreResult;
use crate::kv::KvManager;
use crate::protocol::{ClientMessage, InferResult};

pub trait InferenceBackend: Send {
    fn load(config: &ServerConfig) -> CoreResult<Self>
    where
        Self: Sized;
    fn warmup(&mut self) -> CoreResult<()>;
    fn infer(
        &mut self,
        stage: &str,
        cycle_id: &str,
        prompt_static: &str,
        prompt_variable: &str,
        kv: &mut KvManager,
        max_tokens: u32,
        temperature: f32,
    ) -> CoreResult<InferResult>;
    fn is_ready(&self) -> bool;
}

pub fn infer_from_message<B: InferenceBackend>(
    backend: &mut B,
    kv: &mut KvManager,
    message: &ClientMessage,
) -> CoreResult<InferResult> {
    let ClientMessage::Infer {
        cycle_id,
        stage,
        prompt,
        max_tokens,
        temperature,
        ..
    } = message
    else {
        return Err(crate::error::CoreError::Inference(
            "expected infer message".into(),
        ));
    };

    let plan = kv.prepare_cycle_stage(cycle_id, prompt);
    tracing::debug!(
        cycle_id = %cycle_id,
        stage = %stage,
        prefill_static = plan.prefill_static,
        restored = plan.restored_from_snapshot,
        "kv plan prepared"
    );

    backend.infer(
        stage,
        cycle_id,
        &prompt.static_prefix,
        &prompt.variable_text(),
        kv,
        *max_tokens,
        *temperature,
    )
}
