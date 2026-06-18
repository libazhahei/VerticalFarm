//! llama.cpp production backend for Jetson / cross-compiled edge targets.

#[cfg(feature = "llama")]
pub mod ffi;
#[cfg(feature = "llama")]
mod session;

pub mod runtime;

pub use runtime::{LlamaBackend, LlamaRuntime};
