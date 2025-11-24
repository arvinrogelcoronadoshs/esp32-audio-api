from flask import Flask, request, jsonify
import numpy as np
import wave
from scipy.signal import resample
import io
import requests
from datetime import datetime

app = Flask(__name__)

SKILLORA_UPLOAD_URL = "https://skillora.space/uploads/upload_audio.php"  # your upload API

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

        # Save WAV to memory buffer
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(samples_pcm.tobytes())
        wav_buffer.seek(0)

        # Upload to Skillora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files = {'file': (f'audio_{timestamp}.wav', wav_buffer, 'audio/wav')}
        response = requests.post(SKILLORA_UPLOAD_URL, files=files)

        if response.status_code == 200:
            return jsonify({"status": "success", "skillora_response": response.text}), 200
        else:
            return jsonify({"status": "error", "skillora_response": response.text}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
