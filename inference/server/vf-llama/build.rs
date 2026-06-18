//! Link against a prebuilt llama.cpp when the `llama` feature is enabled.
//!
//! # Cross-compilation (Jetson Orin, aarch64-linux-gnu)
//!
//! Build llama.cpp on the device or in a sysroot, then point Cargo at the artifacts:
//!
//! ```bash
//! export LLAMA_CPP_DIR=/opt/llama.cpp          # optional root
//! export LLAMA_LIB_DIR=/opt/llama.cpp/build    # directory containing libllama.a / libggml.a
//! export LLAMA_INCLUDE_DIR=/opt/llama.cpp/include
//!
//! # Optional: CUDA-enabled ggml (Jetson)
//! export VF_LLAMA_CUDA=1
//!
//! # Cross toolchain example
//! export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
//! cargo build --release -p vf-server \
//!   --features llama \
//!   --target aarch64-unknown-linux-gnu
//! ```
//!
//! Environment variables honoured by this script:
//! - `LLAMA_CPP_DIR` — root of llama.cpp checkout / install prefix
//! - `LLAMA_LIB_DIR` — native library search path (defaults to `$LLAMA_CPP_DIR/build`)
//! - `LLAMA_INCLUDE_DIR` — headers (defaults to `$LLAMA_CPP_DIR/include` or `.../ggml/include`)
//! - `VF_LLAMA_CUDA` — when `1`, link `cudart` / `cublas` / `cublasLt`
//! - `VF_LLAMA_STATIC` — when `1` (default), prefer static `libllama.a` / `libggml.a`

use std::env;
use std::path::{Path, PathBuf};

fn main() {
    println!("cargo:rerun-if-env-changed=LLAMA_CPP_DIR");
    println!("cargo:rerun-if-env-changed=LLAMA_LIB_DIR");
    println!("cargo:rerun-if-env-changed=LLAMA_INCLUDE_DIR");
    println!("cargo:rerun-if-env-changed=VF_LLAMA_CUDA");
    println!("cargo:rerun-if-env-changed=VF_LLAMA_STATIC");
    println!("cargo:rerun-if-changed=build.rs");

    if !cfg_enabled("CARGO_FEATURE_LLAMA") {
        return;
    }

    let lib_dir = resolve_lib_dir();
    let include_dir = resolve_include_dir();

    if let Some(dir) = &lib_dir {
        println!("cargo:rustc-link-search=native={}", dir.display());
    } else {
        println!(
            "cargo:warning=LLAMA_LIB_DIR / LLAMA_CPP_DIR not set; link step expects libllama on the default search path"
        );
    }

    if let Some(dir) = &include_dir {
        println!("cargo:include={}", dir.display());
    }

    let static_link = env::var("VF_LLAMA_STATIC")
        .map(|value| value != "0")
        .unwrap_or(true);

    link_llama_libs(static_link);

    if env::var("VF_LLAMA_CUDA").map(|value| value == "1").unwrap_or(false)
        || cfg_enabled("CARGO_FEATURE_CUDA")
    {
        println!("cargo:rustc-link-lib=cudart");
        println!("cargo:rustc-link-lib=cublas");
        println!("cargo:rustc-link-lib=cublasLt");
    }

    // llama.cpp is C++; Linux/Jetson sysroots need these.
    println!("cargo:rustc-link-lib=stdc++");
    println!("cargo:rustc-link-lib=pthread");
    println!("cargo:rustc-link-lib=dl");
    println!("cargo:rustc-link-lib=m");

    let target = env::var("TARGET").unwrap_or_default();
    if target.contains("linux") {
        // Common on aarch64 Jetson rootfs when using OpenBLAS-enabled ggml builds.
        if lib_dir
            .as_ref()
            .is_some_and(|dir| dir.join("libopenblas.so").exists() || dir.join("libopenblas.a").exists())
        {
            println!("cargo:rustc-link-lib=openblas");
        }
    }
}

fn cfg_enabled(name: &str) -> bool {
    env::var(name).map(|value| value == "1").unwrap_or(false)
}

fn resolve_lib_dir() -> Option<PathBuf> {
    if let Ok(path) = env::var("LLAMA_LIB_DIR") {
        return Some(PathBuf::from(path));
    }
    env::var("LLAMA_CPP_DIR")
        .ok()
        .map(|root| PathBuf::from(root).join("build"))
        .filter(|path| path.exists())
}

fn resolve_include_dir() -> Option<PathBuf> {
    if let Ok(path) = env::var("LLAMA_INCLUDE_DIR") {
        return Some(PathBuf::from(path));
    }
    if let Ok(root) = env::var("LLAMA_CPP_DIR") {
        let root = PathBuf::from(root);
        for candidate in [root.join("include"), root.join("ggml/include")] {
            if candidate.join("llama.h").exists() {
                return Some(candidate);
            }
        }
    }
    None
}

fn link_llama_libs(static_link: bool) {
    if static_link {
        println!("cargo:rustc-link-lib=static=llama");
        println!("cargo:rustc-link-lib=static=ggml");
        // Newer llama.cpp splits ggml backends into separate archives.
        for lib in ["ggml-base", "ggml-cpu", "ggml-cuda"] {
            if lib_exists(lib) {
                println!("cargo:rustc-link-lib=static={lib}");
            }
        }
        return;
    }

    println!("cargo:rustc-link-lib=llama");
    println!("cargo:rustc-link-lib=ggml");
}

fn lib_exists(name: &str) -> bool {
    let lib_dir = resolve_lib_dir();
    let Some(dir) = lib_dir else {
        return false;
    };
    static_extensions(name, &dir)
}

fn static_extensions(name: &str, dir: &Path) -> bool {
    ["a", "so"].iter().any(|ext| dir.join(format!("lib{name}.{ext}")).exists())
}
