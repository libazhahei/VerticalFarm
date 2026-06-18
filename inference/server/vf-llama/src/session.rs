//! Single-model llama.cpp session: load, prefill, decode, KV snapshot.

use std::collections::HashMap;
use std::ffi::CString;
use std::os::raw::c_char;
use std::ptr;
use std::time::Instant;

use vf_core::error::{CoreError, CoreResult};
use vf_core::kv::KvStagePlan;
use vf_core::protocol::{InferMetrics, InferResult};

use crate::ffi::{
    self, check_decode_status, is_oom_message, llama_batch, llama_context, llama_context_params,
    llama_model, llama_model_params, llama_sampler, llama_token, llama_vocab,
};

const MAX_PROMPT_TOKENS: i32 = 8192;
const TOKEN_PIECE_BUF: i32 = 256;
const DEFAULT_SEQ_ID: i32 = 0;

pub struct LlamaSession {
    model: *mut llama_model,
    ctx: *mut llama_context,
    vocab: *const llama_vocab,
    eos_token: llama_token,
    n_ctx: u32,
    n_batch: u32,
    model_name: String,
    model_path: String,
    kv_snapshots: HashMap<String, Vec<u8>>,
}

// llama contexts are not Sync; vf-server holds ModelRuntime behind a Mutex.
unsafe impl Send for LlamaSession {}

impl LlamaSession {
    pub fn load(
        model_name: &str,
        model_path: &str,
        n_ctx: u32,
        n_batch: u32,
        n_gpu_layers: i32,
        n_threads: i32,
    ) -> CoreResult<Self> {
        let path = CString::new(model_path)
            .map_err(|_| CoreError::Inference("model path contains NUL byte".into()))?;

        let mut model_params = unsafe { ffi::llama_model_default_params() };
        model_params.use_mmap = true;
        model_params.use_mlock = false;
        model_params.n_gpu_layers = n_gpu_layers;

        let model = unsafe { ffi::llama_model_load_from_file(path.as_ptr(), model_params) };
        if model.is_null() {
            return Err(CoreError::Inference(format!(
                "failed to load model {model_name} from {model_path}"
            )));
        }

        let ctx_params = context_params(n_ctx, n_batch, n_threads);
        let ctx = unsafe { ffi::llama_init_from_model(model, ctx_params) };
        if ctx.is_null() {
            unsafe { ffi::llama_model_free(model) };
            return Err(CoreError::Inference(format!(
                "failed to create llama context for {model_name} (OOM?)"
            )));
        }

        let vocab = unsafe { ffi::llama_model_get_vocab(model) };
        let eos_token = unsafe { ffi::llama_vocab_eos(vocab) };
        let actual_n_ctx = unsafe { ffi::llama_n_ctx(ctx) };

        tracing::info!(
            model = %model_name,
            path = %model_path,
            n_ctx = actual_n_ctx,
            n_gpu_layers = n_gpu_layers,
            "llama model loaded"
        );

        Ok(Self {
            model,
            ctx,
            vocab,
            eos_token,
            n_ctx: actual_n_ctx,
            n_batch,
            model_name: model_name.to_string(),
            model_path: model_path.to_string(),
            kv_snapshots: HashMap::new(),
        })
    }

    pub fn model_name(&self) -> &str {
        &self.model_name
    }

    pub fn warmup(&mut self) -> CoreResult<()> {
        self.reset_kv()?;
        let tokens = self.tokenize("Ready.", true)?;
        self.decode_prompt(&tokens)?;
        tracing::info!(model = %self.model_name, "warmup decode complete");
        self.reset_kv()?;
        Ok(())
    }

    pub fn infer(
        &mut self,
        cycle_id: &str,
        static_prefix: &str,
        prompt_variable: &str,
        plan: &KvStagePlan,
        max_tokens: u32,
        temperature: f32,
    ) -> CoreResult<InferResult> {
        let started = Instant::now();
        let mut prefill_tokens: u32 = 0;

        if plan.prefill_static {
            self.reset_kv()?;
            let static_tokens = self.tokenize(static_prefix, true)?;
            prefill_tokens += static_tokens.len() as u32;
            self.decode_prompt(&static_tokens)?;
            self.save_kv_snapshot(cycle_id)?;
        } else if plan.restored_from_snapshot {
            self.restore_kv_snapshot(cycle_id)?;
        } else {
            self.reset_kv()?;
        }

        let variable_tokens = self.tokenize(prompt_variable, false)?;
        prefill_tokens += variable_tokens.len() as u32;
        self.decode_prompt(&variable_tokens)?;

        let prefill_ms = started.elapsed().as_millis() as u64;
        let decode_started = Instant::now();
        let generated = self.generate(max_tokens, temperature)?;
        let decode_ms = decode_started.elapsed().as_millis() as u64;

        Ok(InferResult {
            output: generated.text,
            metrics: InferMetrics {
                prefill_ms,
                decode_ms,
                prefill_tokens,
                decode_tokens: generated.decode_tokens,
            },
        })
    }

    fn reset_kv(&mut self) -> CoreResult<()> {
        unsafe { ffi::llama_kv_self_clear(self.ctx) };
        Ok(())
    }

    fn save_kv_snapshot(&mut self, cycle_id: &str) -> CoreResult<()> {
        let size = unsafe { ffi::llama_state_get_size(self.ctx) };
        if size == 0 {
            return Err(CoreError::Inference("llama_state_get_size returned 0".into()));
        }
        let mut buffer = vec![0u8; size];
        let written =
            unsafe { ffi::llama_state_get_data(self.ctx, buffer.as_mut_ptr(), buffer.len()) };
        if written != size {
            return Err(CoreError::Inference(format!(
                "llama_state_get_data wrote {written} of {size} bytes"
            )));
        }
        self.kv_snapshots.insert(cycle_id.to_string(), buffer);
        Ok(())
    }

    fn restore_kv_snapshot(&mut self, cycle_id: &str) -> CoreResult<()> {
        let snapshot = self
            .kv_snapshots
            .get(cycle_id)
            .cloned()
            .ok_or_else(|| CoreError::Inference(format!("missing KV snapshot for cycle {cycle_id}")))?;
        self.reset_kv()?;
        let restored = unsafe {
            ffi::llama_state_set_data(self.ctx, snapshot.as_ptr(), snapshot.len())
        };
        if restored != snapshot.len() {
            return Err(CoreError::Inference(format!(
                "llama_state_set_data restored {restored} of {} bytes",
                snapshot.len()
            )));
        }
        Ok(())
    }

    fn tokenize(&self, text: &str, add_special: bool) -> CoreResult<Vec<llama_token>> {
        let c_text = CString::new(text)
            .map_err(|_| CoreError::Inference("prompt contains NUL byte".into()))?;
        let mut tokens = vec![0i32; MAX_PROMPT_TOKENS as usize];
        let count = unsafe {
            ffi::llama_tokenize(
                self.vocab,
                c_text.as_ptr(),
                text.len() as i32,
                tokens.as_mut_ptr(),
                tokens.len() as i32,
                add_special,
                true,
            )
        };
        if count < 0 {
            return Err(CoreError::Inference(format!(
                "tokenization failed for {} chars (buffer too small?)",
                text.len()
            )));
        }
        tokens.truncate(count as usize);
        Ok(tokens)
    }

    fn decode_prompt(&mut self, tokens: &[llama_token]) -> CoreResult<()> {
        if tokens.is_empty() {
            return Ok(());
        }

        let mut prompt = tokens.to_vec();
        let mut offset = 0usize;
        while offset < prompt.len() {
            let chunk_end = (offset + self.n_batch as usize).min(prompt.len());
            let chunk = &mut prompt[offset..chunk_end];
            let mut batch =
                unsafe { ffi::llama_batch_get_one(chunk.as_mut_ptr(), chunk.len() as i32) };
            self.set_batch_positions(&mut batch, offset);
            let status = unsafe { ffi::llama_decode(self.ctx, batch) };
            check_decode_status(status).map_err(map_llama_error)?;
            offset = chunk_end;
        }
        Ok(())
    }

    fn set_batch_positions(&self, batch: &mut llama_batch, offset: usize) {
        if batch.pos.is_null() || batch.n_tokens <= 0 {
            return;
        }
        unsafe {
            for index in 0..batch.n_tokens as isize {
                *batch.pos.offset(index) = (offset as i32) + index as i32;
            }
            if !batch.n_seq_id.is_null() {
                for index in 0..batch.n_tokens as isize {
                    *batch.n_seq_id.offset(index) = 1;
                }
            }
            if !batch.seq_id.is_null() {
                for index in 0..batch.n_tokens as isize {
                    let slot = batch.seq_id.offset(index);
                    if !(*slot).is_null() {
                        *(*slot).offset(0) = DEFAULT_SEQ_ID;
                    }
                }
            }
        }
    }

    fn generate(&mut self, max_tokens: u32, temperature: f32) -> CoreResult<GenerateOutput> {
        let sampler = SamplerChain::new(temperature)?;
        let mut output = String::new();
        let mut decode_tokens = 0u32;

        for _ in 0..max_tokens {
            let token = unsafe { ffi::llama_sampler_sample(sampler.chain, self.ctx, -1) };
            if token == self.eos_token {
                break;
            }

            output.push_str(&self.token_to_piece(token)?);
            decode_tokens += 1;

            unsafe { ffi::llama_sampler_accept(sampler.chain, token) };

            let mut next = token;
            let batch = unsafe { ffi::llama_batch_get_one(&mut next, 1) };
            let status = unsafe { ffi::llama_decode(self.ctx, batch) };
            check_decode_status(status).map_err(map_llama_error)?;
        }

        Ok(GenerateOutput {
            text: output,
            decode_tokens,
        })
    }

    fn token_to_piece(&self, token: llama_token) -> CoreResult<String> {
        let mut buffer = vec![0i8; TOKEN_PIECE_BUF as usize];
        let length = unsafe {
            ffi::llama_token_to_piece(
                self.vocab,
                token,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as i32,
                0,
                false,
            )
        };
        if length < 0 {
            return Err(CoreError::Inference(format!(
                "llama_token_to_piece failed for token {token}"
            )));
        }
        buffer.truncate(length as usize);
        let piece = String::from_utf8_lossy(
            &buffer.iter().map(|byte| *byte as u8).collect::<Vec<_>>(),
        )
        .into_owned();
        Ok(piece)
    }
}

impl Drop for LlamaSession {
    fn drop(&mut self) {
        unsafe {
            if !self.ctx.is_null() {
                ffi::llama_free(self.ctx);
            }
            if !self.model.is_null() {
                ffi::llama_model_free(self.model);
            }
        }
    }
}

struct GenerateOutput {
    text: String,
    decode_tokens: u32,
}

struct SamplerChain {
    chain: *mut llama_sampler,
}

impl SamplerChain {
    fn new(temperature: f32) -> CoreResult<Self> {
        let params = unsafe { ffi::llama_sampler_chain_default_params() };
        let chain = unsafe { ffi::llama_sampler_chain_init(params) };
        if chain.is_null() {
            return Err(CoreError::Inference("llama_sampler_chain_init failed".into()));
        }

        let temp = unsafe { ffi::llama_sampler_init_temp(temperature.max(0.01)) };
        let dist = unsafe { ffi::llama_sampler_init_dist(0x1234_5678) };
        if temp.is_null() || dist.is_null() {
            unsafe { ffi::llama_sampler_free(chain) };
            return Err(CoreError::Inference("sampler init failed".into()));
        }

        unsafe {
            ffi::llama_sampler_chain_add(chain, temp);
            ffi::llama_sampler_chain_add(chain, dist);
        }

        Ok(Self { chain })
    }
}

impl Drop for SamplerChain {
    fn drop(&mut self) {
        if !self.chain.is_null() {
            unsafe { ffi::llama_sampler_free(self.chain) };
        }
    }
}

fn context_params(n_ctx: u32, n_batch: u32, n_threads: i32) -> llama_context_params {
    let mut params = unsafe { ffi::llama_context_default_params() };
    params.n_ctx = n_ctx;
    params.n_batch = n_batch.max(512);
    params.n_ubatch = params.n_batch;
    params.n_threads = n_threads.max(1);
    params.n_threads_batch = n_threads.max(1);
    params
}

fn map_llama_error(message: String) -> CoreError {
    if is_oom_message(&message) {
        CoreError::Inference("out of memory".into())
    } else {
        CoreError::Inference(message)
    }
}

pub fn log_system_info() {
    let info = unsafe { ffi::llama_print_system_info() };
    if info.is_null() {
        return;
    }
    let text = unsafe {
        std::ffi::CStr::from_ptr(info)
            .to_string_lossy()
            .into_owned()
    };
    tracing::info!(%text, "llama.cpp system info");
}

// Silence unused import warning for model params type used in signatures.
const _: () = {
    let _ = ptr::null::<llama_model_params>();
};
