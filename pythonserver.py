from fastapi import FastAPI, Request
import uvicorn
import numpy as np
import wave
import struct
import os
from scipy.signal import resample
from datetime import datetime

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SAMPLE_RATE = 8000
RECORD_SECONDS = 10
NUM_SAMPLES = SAMPLE_RATE * RECORD_SECONDS

@app.post("/upload_audio")
async def upload_audio(request: Request):
    raw = await request.body()
    expected_bytes = NUM_SAMPLES * 2  # 2 bytes per sample

    if len(raw) != expected_bytes:
        return {"status": "error", "message": f"Incorrect data length. Expected {expected_bytes}, got {len(raw)}"}

    # Convert bytes to integers
    samples = [struct.unpack('>H', raw[i:i+2])[0] for i in range(0, len(raw), 2)]

    # Convert to float -1..1
    samples = np.array(samples, dtype=np.float32)
    samples = (samples / 4095.0) * 2 - 1

    # Resample & pitch modify
    samples = resample(samples, NUM_SAMPLES)
    samples = resample(samples, int(NUM_SAMPLES / 0.65))
    samples = np.clip(samples, -1.0, 1.0)

    # Convert to PCM16
    samples_int16 = (samples * 32767).astype(np.int16)

    # Save WAV
    filename = datetime.now().strftime("audio_%Y%m%d_%H%M%S.wav")
    path = os.path.join(UPLOAD_DIR, filename)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples_int16.tobytes())

    return {"status": "OK", "file": filename}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
