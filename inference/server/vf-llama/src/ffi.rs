//! Raw FFI bindings for llama.cpp (C API).
//!
//! The surface area is intentionally small: model/context lifecycle, tokenization,
//! batch decode, sampler chain, and KV-state save/restore for multi-stage workflows.

#![allow(non_camel_case_types, dead_code, improper_ctypes)]

use std::os::raw::{c_char, c_float, c_void};

pub type llama_token = i32;
pub type llama_pos = i32;
pub type llama_seq_id = i32;

#[repr(C)]
pub struct llama_model {
    _private: [u8; 0],
}

#[repr(C)]
pub struct llama_context {
    _private: [u8; 0],
}

#[repr(C)]
pub struct llama_vocab {
    _private: [u8; 0],
}

#[repr(C)]
pub struct llama_sampler {
    _private: [u8; 0],
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct llama_model_params {
    pub devices: *const c_void,
    pub tensor_split: *const c_float,
    pub progress_callback: Option<
        unsafe extern "C" fn(progress: f32, user_data: *mut c_void) -> bool,
    >,
    pub progress_callback_user_data: *mut c_void,
    pub kv_overrides: *const c_void,
    pub vocab_only: bool,
    pub use_mmap: bool,
    pub use_mlock: bool,
    pub check_tensors: bool,
    pub n_gpu_layers: i32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct llama_context_params {
    pub n_ctx: u32,
    pub n_batch: u32,
    pub n_ubatch: u32,
    pub n_seq_max: u32,
    pub n_threads: i32,
    pub n_threads_batch: i32,
    pub rope_scaling_type: i32,
    pub pooling_type: i32,
    pub attention_type: i32,
    pub rope_freq_base: f32,
    pub rope_freq_scale: f32,
    pub yarn_ext_factor: f32,
    pub yarn_attn_factor: f32,
    pub yarn_beta_fast: f32,
    pub yarn_beta_slow: f32,
    pub yarn_orig_ctx: u32,
    pub defrag_thold: f32,
    pub cb_eval: Option<unsafe extern "C" fn(*mut c_void, *mut c_void, bool) -> bool>,
    pub cb_eval_user_data: *mut c_void,
    pub type_k: i32,
    pub type_v: i32,
    pub abort_callback: Option<unsafe extern "C" fn(*mut c_void) -> bool>,
    pub abort_callback_data: *mut c_void,
    pub embeddings: bool,
    pub offload_kqv: bool,
    pub flash_attn: bool,
    pub no_perf: bool,
    pub op_offload: bool,
    pub swa_full: bool,
    pub kv_unified: bool,
}

#[repr(C)]
pub struct llama_batch {
    pub n_tokens: i32,
    pub token: *mut llama_token,
    pub embd: *mut c_float,
    pub pos: *mut llama_pos,
    pub n_seq_id: *mut i32,
    pub seq_id: *mut *mut llama_seq_id,
    pub logits: *mut i8,
}

#[repr(C)]
pub struct llama_sampler_chain_params {
    pub no_perf: bool,
}

extern "C" {
    pub fn llama_backend_init() -> ();
    pub fn llama_backend_free() -> ();

    pub fn llama_model_default_params() -> llama_model_params;
    pub fn llama_context_default_params() -> llama_context_params;
    pub fn llama_sampler_chain_default_params() -> llama_sampler_chain_params;

    pub fn llama_model_load_from_file(
        path_model: *const c_char,
        params: llama_model_params,
    ) -> *mut llama_model;
    pub fn llama_model_free(model: *mut llama_model);

    pub fn llama_init_from_model(
        model: *mut llama_model,
        params: llama_context_params,
    ) -> *mut llama_context;
    pub fn llama_free(ctx: *mut llama_context);

    pub fn llama_model_get_vocab(model: *const llama_model) -> *const llama_vocab;
    pub fn llama_vocab_eos(vocab: *const llama_vocab) -> llama_token;
    pub fn llama_vocab_bos(vocab: *const llama_vocab) -> llama_token;

    pub fn llama_n_ctx(ctx: *const llama_context) -> u32;

    pub fn llama_tokenize(
        vocab: *const llama_vocab,
        text: *const c_char,
        text_len: i32,
        tokens: *mut llama_token,
        n_tokens_max: i32,
        add_special: bool,
        parse_special: bool,
    ) -> i32;

    pub fn llama_token_to_piece(
        vocab: *const llama_vocab,
        token: llama_token,
        buf: *mut c_char,
        length: i32,
        lstrip: i32,
        special: bool,
    ) -> i32;

    pub fn llama_batch_get_one(
        tokens: *mut llama_token,
        n_tokens: i32,
    ) -> llama_batch;

    pub fn llama_decode(ctx: *mut llama_context, batch: llama_batch) -> i32;

    pub fn llama_get_logits_ith(ctx: *const llama_context, i: i32) -> *const c_float;

    pub fn llama_state_get_size(ctx: *const llama_context) -> usize;
    pub fn llama_state_get_data(ctx: *const llama_context, dst: *mut u8, size: usize) -> usize;
    pub fn llama_state_set_data(ctx: *mut llama_context, src: *const u8, size: usize) -> usize;

    pub fn llama_kv_self_clear(ctx: *mut llama_context) -> ();

    pub fn llama_sampler_chain_init(params: llama_sampler_chain_params) -> *mut llama_sampler;
    pub fn llama_sampler_chain_add(chain: *mut llama_sampler, smpl: *mut llama_sampler);
    pub fn llama_sampler_init_temp(t: f32) -> *mut llama_sampler;
    pub fn llama_sampler_init_dist(seed: u32) -> *mut llama_sampler;
    pub fn llama_sampler_sample(
        smpl: *mut llama_sampler,
        ctx: *mut llama_context,
        idx: i32,
    ) -> llama_token;
    pub fn llama_sampler_accept(smpl: *mut llama_sampler, token: llama_token) -> ();
    pub fn llama_sampler_free(smpl: *mut llama_sampler) -> ();

    pub fn llama_print_system_info() -> *const c_char;
}

pub fn check_decode_status(status: i32) -> Result<(), String> {
    if status == 0 {
        Ok(())
    } else {
        Err(format!("llama_decode failed with status {status}"))
    }
}

pub fn is_oom_message(message: &str) -> bool {
    vf_core::models::ModelRegistry::is_oom_error(message)
}
