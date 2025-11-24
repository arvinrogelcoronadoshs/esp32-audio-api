from flask import Flask, request
import numpy as np
import wave
from scipy.signal import resample
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        raw_data = request.data
        num_samples = len(raw_data) // 2
        samples = np.frombuffer(raw_data, dtype=np.uint16).astype(np.float32)
        samples = (samples / 4095.0) * 2 - 1  # normalize

        # Resample / pitch correction
        samples_resampled = resample(samples, num_samples)
        samples_resampled = resample(samples_resampled, int(num_samples / 0.65))
        samples_resampled = np.clip(samples_resampled, -1.0, 1.0)
        samples_pcm = (samples_resampled * 32767).astype(np.int16)

        # Save WAV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = os.path.join(UPLOAD_DIR, f"audio_{timestamp}.wav")
        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(samples_pcm.tobytes())

        return {"status": "success", "file": wav_path}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
