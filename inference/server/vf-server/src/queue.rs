use std::sync::Arc;

use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Mutex;
use vf_core::error::CoreResult;
use vf_core::model_manager::ModelRuntime;
use vf_core::protocol::{decode_client_message, encode_message, ClientMessage, ServerMessage};
use vf_core::service::InferenceService;

use crate::frame::{read_frame, write_frame};

pub async fn run_tcp_server<R: ModelRuntime + 'static>(
    port: u16,
    service: Arc<Mutex<InferenceService<R>>>,
) -> CoreResult<()> {
    let listener = TcpListener::bind(("0.0.0.0", port)).await?;
    tracing::info!(port = port, "vf-server listening");

    loop {
        let (stream, addr) = listener.accept().await?;
        tracing::info!(%addr, "client connected");
        let service = Arc::clone(&service);
        tokio::spawn(async move {
            if let Err(error) = handle_connection(stream, service).await {
                tracing::warn!(%addr, %error, "connection closed with error");
            } else {
                tracing::info!(%addr, "connection closed");
            }
        });
    }
}

async fn handle_connection<R: ModelRuntime + 'static>(
    stream: TcpStream,
    service: Arc<Mutex<InferenceService<R>>>,
) -> CoreResult<()> {
    let (reader, writer) = stream.into_split();
    let reader = Arc::new(Mutex::new(reader));
    let writer = Arc::new(Mutex::new(writer));
    let infer_lock = Arc::new(Mutex::new(()));

    loop {
        let body = {
            let mut reader = reader.lock().await;
            read_frame(&mut *reader).await?
        };

        let message = decode_client_message(&body)?;
        let response = dispatch_message(&service, &infer_lock, message).await;
        let frame = encode_message(&response)?;
        let mut writer = writer.lock().await;
        write_frame(&mut *writer, &frame).await?;
    }
}

async fn dispatch_message<R: ModelRuntime + 'static>(
    service: &Arc<Mutex<InferenceService<R>>>,
    infer_lock: &Arc<Mutex<()>>,
    message: ClientMessage,
) -> ServerMessage {
    match message {
        ClientMessage::Heartbeat { .. } => {
            let service = service.lock().await;
            service.heartbeat_ack()
        }
        ClientMessage::FlushCache { .. } => {
            let mut service = service.lock().await;
            service.handle_flush_cache()
        }
        ClientMessage::CycleEnd { cycle_id } => {
            let mut service = service.lock().await;
            service.handle_cycle_end(&cycle_id)
        }
        ClientMessage::Preload { models } => {
            let mut service = service.lock().await;
            match service.handle_preload(&models) {
                Ok(response) => response,
                Err(error) => ServerMessage::Error {
                    code: "preload_failed".into(),
                    message: error.to_string(),
                    request_id: None,
                },
            }
        }
        ref infer_msg @ ClientMessage::Infer { ref request_id, .. } => {
            let _guard = infer_lock.lock().await;
            let mut service = service.lock().await;
            match service.handle_infer(infer_msg) {
                Ok(response) => response,
                Err(error) => ServerMessage::Error {
                    code: "infer_failed".into(),
                    message: error.to_string(),
                    request_id: Some(request_id.clone()),
                },
            }
        }
    }
}
