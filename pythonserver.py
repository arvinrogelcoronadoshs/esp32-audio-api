from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import os
from datetime import datetime
import wave
import numpy as np
from scipy.signal import resample

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
TEMP_FILE = os.path.join(UPLOAD_DIR, "audio_temp.raw")

SAMPLE_RATE = 8000
RECORD_SECONDS = 10
NUM_SAMPLES = SAMPLE_RATE * RECORD_SECONDS

# --------------------------
# Download endpoint
# --------------------------
@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, filename=filename)
    return {"status": "error", "message": "File not found"}

# --------------------------
# Upload audio chunks
# --------------------------
@app.post("/upload_audio_chunk")
async def upload_audio_chunk(request: Request):
    raw = await request.body()
    if len(raw) == 0:
        return {"status":"error", "message":"Empty data"}

    # Append chunk to temporary file
    with open(TEMP_FILE, "ab") as f:
        f.write(raw)

    # Check if we have all samples
    file_size = os.path.getsize(TEMP_FILE)
    expected_size = NUM_SAMPLES * 2  # 16-bit PCM
    if file_size >= expected_size:
        # Read raw data
        with open(TEMP_FILE, "rb") as f:
            raw_data = f.read()
        samples = [int.from_bytes(raw_data[i:i+2], 'big') for i in range(0, len(raw_data), 2)]
        samples = np.array(samples, dtype=np.float32)

        # Convert ADC 0-4095 -> -1.0..1.0
        samples = (samples / 4095.0) * 2 - 1

        # Resample to exact number of samples for RECORD_SECONDS
        samples_resampled = resample(samples, NUM_SAMPLES)

        # Optional: pitch modification (~lower pitch 35%)
        samples_resampled = resample(samples_resampled, int(NUM_SAMPLES / 0.65))

        # Clip to -1..1
        samples_resampled = np.clip(samples_resampled, -1.0, 1.0)

        # Convert to 16-bit PCM
        samples_pcm = (samples_resampled * 32767).astype(np.int16)

        # Save WAV
        filename = datetime.now().strftime("audio_%Y%m%d_%H%M%S.wav")
        path = os.path.join(UPLOAD_DIR, filename)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(samples_pcm.tobytes())

        # Remove temp raw file
        os.remove(TEMP_FILE)

        return {"status":"OK", "file": filename}

    return {"status":"OK", "message": f"Received {len(raw)} bytes"}
