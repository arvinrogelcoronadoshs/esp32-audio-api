from fastapi import FastAPI, Request
import os
from datetime import datetime
import wave
import numpy as np
from scipy.signal import resample

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
TEMP_FILE = os.path.join(UPLOAD_DIR, "audio_temp.raw")

from fastapi.responses import FileResponse

UPLOAD_DIR = "uploads"

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, filename=filename)
    return {"status": "error", "message": "File not found"}




SAMPLE_RATE = 8000

@app.post("/upload_audio_chunk")
async def upload_audio_chunk(request: Request):
    raw = await request.body()
    if len(raw) == 0:
        return {"status":"error", "message":"Empty data"}

    # Append chunk to temp raw file
    with open(TEMP_FILE, "ab") as f:
        f.write(raw)

    # If this is the last chunk, convert to WAV
    # Optional: you can send a finalization request or trigger conversion manually
    # For demonstration, let's assume 10 chunks → 10s
    file_size = os.path.getsize(TEMP_FILE)
    expected_size = SAMPLE_RATE * 10 * 2  # 10s, 16-bit PCM

    if file_size >= expected_size:
        # Convert raw to WAV
        with open(TEMP_FILE, "rb") as f:
            raw_data = f.read()
        samples = [int.from_bytes(raw_data[i:i+2], 'big') for i in range(0, len(raw_data), 2)]
        samples = np.array(samples, dtype=np.float32)
        samples = (samples / 4095.0) * 2 - 1
        samples = resample(samples, SAMPLE_RATE*10)  # resample if needed
        samples = np.clip(samples, -1.0, 1.0)
        samples_int16 = (samples*32767).astype(np.int16)

        filename = datetime.now().strftime("audio_%Y%m%d_%H%M%S.wav")
        path = os.path.join(UPLOAD_DIR, filename)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(samples_int16.tobytes())

        # Remove temp file
        os.remove(TEMP_FILE)

        return {"status":"OK", "file": filename}

    return {"status":"OK", "message": f"Received {len(raw)} bytes"}
