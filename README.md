# XTTS Streaming

This is a FastAPI service that provides streaming text-to-speech using [XTTS v2](https://github.com/coqui-ai/TTS).

TTS is a generative audio model for text-to-speech generation. This model takes in text and converts it to speech with real-time streaming support.

## Installation

First, clone this repository:

```sh
git clone https://github.com/basetenlabs/truss-examples/
cd xtts-streaming
```

Install dependencies:

```sh
pip install -r requirements.txt
```

**Note**: This requires a CUDA-capable GPU. The model uses DeepSpeed for optimization.

## Running the Service

Set the required environment variable and start the server:

```sh
export COQUI_TOS_AGREED=1
uvicorn app:app --host 0.0.0.0 --port 8000
```

Or use the provided script:

```sh
./run.sh
```

The API will be available at `http://localhost:8000`

API documentation is available at `http://localhost:8000/docs`

## API Endpoints

### `POST /synthesize`
Returns streaming PCM audio (raw 16-bit, 24kHz, mono)

### `POST /synthesize-wav`
Returns complete WAV file

### Request Body

```json
{
  "text": "Text to convert to speech",
  "language": "en",
  "chunk_size": 20
}
```

**Parameters:**
- `text` (required): The text to convert into speech
- `language` (optional, default: "en"): Language code (e.g., "en", "es", "fr", "de")
- `chunk_size` (optional, default: 20): Integer size of each chunk for streaming (1-100)

## Usage Examples

### Example 1: Download as WAV File

The simplest way to get audio is using the `/synthesize-wav` endpoint:

```python
import requests

resp = requests.post(
    "http://localhost:8000/synthesize-wav",
    json={
        "text": "Kurt watched the incoming Pelicans. The blocky jet-powered craft were so distant they were only specks against the setting sun.",
        "language": "en"
    }
)

with open("output.wav", "wb") as f:
    f.write(resp.content)
```

### Example 2: Stream PCM and Save as WAV

Stream raw PCM audio and write to WAV file:

```python
import wave
import requests

text = "Kurt watched the incoming Pelicans. The blocky jet-powered craft were so distant they were only specks against the setting sun. He hit the magnification on his faceplate and saw lines of fire tracing their reentry vectors. They would touch down in three minutes."

resp = requests.post(
    "http://localhost:8000/synthesize",
    json={"text": text, "language": "en", "chunk_size": 20},
    stream=True
)

with wave.open("output.wav", 'wb') as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(24000)  # 24kHz

    for chunk in resp.iter_content(chunk_size=None):
        if chunk:
            wav_file.writeframes(chunk)
```

### Example 3: Real-time Playback with PyAudio

Stream and play audio in real-time as it's generated:

```python
import requests
import pyaudio

text = "Kurt watched the incoming Pelicans. The blocky jet-powered craft were so distant they were only specks against the setting sun."

# Initialize PyAudio
p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=24000,
    output=True
)

# Stream audio
resp = requests.post(
    "http://localhost:8000/synthesize",
    json={"text": text, "language": "en"},
    stream=True
)

# Buffer for smoother playback
buffer = b''
buffer_size_threshold = 2**15  # 32KB

for chunk in resp.iter_content(chunk_size=4096):
    if chunk:
        buffer += chunk
        if len(buffer) >= buffer_size_threshold:
            stream.write(buffer)
            buffer = b''

if buffer:
    stream.write(buffer)

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
```

### Example 4: Using cURL

```sh
# Get WAV file
curl -X POST http://localhost:8000/synthesize-wav \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "language": "en"}' \
  --output speech.wav

# Stream PCM audio
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "language": "en"}' \
  --output speech.pcm
```
# xtts-streaming
