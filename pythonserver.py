from fastapi import FastAPI, Request
import os
from datetime import datetime
import wave
import numpy as np
from scipy.signal import resample
import paramiko  # pip install paramiko

app = FastAPI()

# -----------------------------
# Root route
# -----------------------------
@app.get("/")
def root():
    return {"status": "running", "message": "ESP32 Audio API is live!"}

# -----------------------------
# Local temp storage on Render
# -----------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
TEMP_FILE = os.path.join(UPLOAD_DIR, "audio_temp.raw")

SAMPLE_RATE = 8000  # Hz

# -----------------------------
# SFTP config for skillora.space
# -----------------------------
SFTP_HOST = "skillora.space"
SFTP_PORT = 22
SFTP_USERNAME = "arvin@skillora.space"
SFTP_PASSWORD = "Rishii030625"
SFTP_UPLOAD_DIR = "/uploads"  # e.g., /var/www/html/uploads

def upload_to_skillora(local_path, filename):
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    remote_path = os.path.join(SFTP_UPLOAD_DIR, filename)
    sftp.put(local_path, remote_path)
    sftp.close()
    transport.close()

# -----------------------------
# Download route (optional)
# -----------------------------
from fastapi.responses import FileResponse

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, filename=filename)
    return {"status": "error", "message": "File not found"}

# -----------------------------
# Upload chunk route
# -----------------------------
@app.post("/upload_audio_chunk")
async def upload_audio_chunk(request: Request):
    raw = await request.body()
    if len(raw) == 0:
        return {"status":"error", "message":"Empty data"}

    # Append chunk to temp raw file
    with open(TEMP_FILE, "ab") as f:
        f.write(raw)

    # Check if final size reached (10s)
    file_size = os.path.getsize(TEMP_FILE)
    expected_size = SAMPLE_RATE * 10 * 2  # 10s, 16-bit PCM

    if file_size >= expected_size:
        # Convert raw to WAV
        with open(TEMP_FILE, "rb") as f:
            raw_data = f.read()

        samples = [int.from_bytes(raw_data[i:i+2], 'big') for i in range(0, len(raw_data), 2)]
        samples = np.array(samples, dtype=np.float32)
        samples = (samples / 4095.0) * 2 - 1

        # Resample to exact 10s
        samples = resample(samples, SAMPLE_RATE*10)
        # Pitch manipulation (example: 0.65 factor)
        samples = resample(samples, int(SAMPLE_RATE*10/0.65))
        samples = np.clip(samples, -1.0, 1.0)
        samples_int16 = (samples*32767).astype(np.int16)

        # Save locally on Render first
        filename = datetime.now().strftime("audio_%Y%m%d_%H%M%S.wav")
        local_path = os.path.join(UPLOAD_DIR, filename)
        with wave.open(local_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(samples_int16.tobytes())

        # Upload to skillora.space
        try:
            upload_to_skillora(local_path, filename)
        except Exception as e:
            return {"status":"error", "message": f"Failed to upload to skillora.space: {e}"}

        # Clean up temp file
        os.remove(TEMP_FILE)

        return {"status":"OK", "file": filename}

    return {"status":"OK", "message": f"Received {len(raw)} bytes"}

# -----------------------------
# Run using Render's PORT
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
