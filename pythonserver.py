from flask import Flask, request, jsonify
import os
import numpy as np
import wave
from datetime import datetime
import requests

app = Flask(__name__)

UPLOAD_DIR = "uploads"  # Local temporary storage
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Temporary storage for incoming chunks per client
chunk_storage = {}

# Skillora upload URL (adjust endpoint if needed)
SKILLORA_UPLOAD_URL = "https://skillora.space/uploads/upload_audio.php"

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        # Extract chunk number header
        chunk_number = int(request.headers.get("X-Chunk-Number", 0))
        if chunk_number == 0:
            return jsonify({"status": "error", "message": "Missing X-Chunk-Number header"}), 400

        # Use client IP as session key (simple approach)
        session_id = request.remote_addr

        # Initialize session storage if not exist
        if session_id not in chunk_storage:
            chunk_storage[session_id] = []

        # Append received chunk
        chunk_storage[session_id].append(request.data)

        print(f"Received chunk #{chunk_number} from {session_id}, size={len(request.data)} bytes")

        # Check if we have all samples for 10 seconds of recording (8000 Hz, 2 bytes/sample)
        total_bytes_received = sum(len(c) for c in chunk_storage[session_id])
        expected_bytes = 8000 * 10 * 2  # 10 seconds, 16-bit samples

        if total_bytes_received >= expected_bytes:
            # Merge all chunks
            samples_bytes = b"".join(chunk_storage[session_id])
            samples = np.frombuffer(samples_bytes, dtype=np.uint16).astype(np.int16)

            # Save WAV locally
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_filename = f"audio_{timestamp}.wav"
            wav_path = os.path.join(UPLOAD_DIR, wav_filename)
            with wave.open(wav_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(samples.tobytes())

            print(f"✅ WAV file created locally: {wav_path}")

            # Upload to Skillora
            with open(wav_path, 'rb') as f:
                files = {'file': (wav_filename, f, 'audio/wav')}
                response = requests.post(SKILLORA_UPLOAD_URL, files=files)
                if response.status_code == 200:
                    print(f"✅ WAV file uploaded to Skillora: {wav_filename}")
                    skillora_response = response.text
                else:
                    print(f"❌ Failed to upload to Skillora, HTTP code: {response.status_code}")
                    skillora_response = response.text

            # Clear session storage
            del chunk_storage[session_id]

            return jsonify({
                "status": "success",
                "local_file": wav_path,
                "skillora_response": skillora_response
            }), 200

        # If not all chunks yet
        return jsonify({"status": "chunk_received", "chunk": chunk_number}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
