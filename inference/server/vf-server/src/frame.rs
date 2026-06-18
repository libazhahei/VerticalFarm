use tokio::io::{AsyncReadExt, AsyncWriteExt};
use vf_core::error::{CoreError, CoreResult};

pub async fn read_frame<R: AsyncReadExt + Unpin>(reader: &mut R) -> CoreResult<Vec<u8>> {
    let mut len_buf = [0u8; 4];
    reader.read_exact(&mut len_buf).await?;
    let len = u32::from_be_bytes(len_buf) as usize;
    if len > 16 * 1024 * 1024 {
        return Err(CoreError::Protocol("frame exceeds 16MB limit".into()));
    }
    let mut body = vec![0u8; len];
    reader.read_exact(&mut body).await?;
    Ok(body)
}

pub async fn write_frame<W: AsyncWriteExt + Unpin>(writer: &mut W, frame: &[u8]) -> CoreResult<()> {
    writer.write_all(frame).await?;
    writer.flush().await?;
    Ok(())
}
