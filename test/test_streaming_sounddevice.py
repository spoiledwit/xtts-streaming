import requests
import sounddevice as sd
import numpy as np
import threading
import time

# API endpoint
BASE_URL = "http://localhost:8000/api/v1/xtts"

# Audio settings
SAMPLE_RATE = 24000
CHANNELS = 1
DTYPE = np.int16
CHUNK_SIZE = 4096  # Frames per callback

def test_streaming_sounddevice():
    """Stream and play audio in real-time using sounddevice"""

    print("Real-time audio streaming with sounddevice...")

    payload = {
        "text": (
            "Breaking News — Zoharan Mamdani creates History, the son of Immigrants, becomes the first Indian Muslim American to win NY Mayor Race. Here’s one video how he captured the imagination of a diverse New York."
        ),
        "language": "en",
        "chunk_size": 20
    }

    # Shared state
    audio_buffer = bytearray()
    buffer_lock = threading.Lock()
    download_complete = threading.Event()
    playback_started = threading.Event()

    read_position = 0

    def download_audio():
        """Download audio chunks in background"""
        nonlocal audio_buffer
        try:
            print("Downloading audio chunks...")
            response = requests.post(
                f"{BASE_URL}/synthesize",
                json=payload,
                stream=True
            )

            if response.status_code == 200:
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        with buffer_lock:
                            audio_buffer.extend(chunk)
                        chunk_count += 1

                        # Start playback after buffering some data
                        if chunk_count == 10 and not playback_started.is_set():
                            print("Starting playback...")
                            playback_started.set()

                        if chunk_count % 50 == 0:
                            print(f"Downloaded {chunk_count} chunks ({len(audio_buffer)} bytes buffered)")

                print(f"Download complete! Total: {chunk_count} chunks")
            else:
                print(f"✗ Failed with status code: {response.status_code}")

        except Exception as e:
            print(f"✗ Download error: {str(e)}")
        finally:
            download_complete.set()

    def audio_callback(outdata, frames, time_info, status):
        """Callback to provide audio data to sounddevice"""
        nonlocal read_position

        if status:
            print(f"Audio status: {status}")

        bytes_needed = frames * 2  # 2 bytes per int16 sample

        with buffer_lock:
            available_bytes = len(audio_buffer) - read_position

            if available_bytes >= bytes_needed:
                # We have enough data
                chunk = audio_buffer[read_position:read_position + bytes_needed]
                read_position += bytes_needed

                # Convert to numpy and write
                audio_array = np.frombuffer(chunk, dtype=DTYPE)
                outdata[:] = audio_array.reshape(-1, 1)

            elif download_complete.is_set():
                # Download done but not enough data left
                if available_bytes > 0:
                    # Play remaining data
                    chunk = audio_buffer[read_position:]
                    read_position = len(audio_buffer)
                    audio_array = np.frombuffer(chunk, dtype=DTYPE)
                    # Pad with silence
                    padded = np.pad(audio_array, (0, frames - len(audio_array)))
                    outdata[:] = padded.reshape(-1, 1)
                else:
                    # No more data
                    raise sd.CallbackStop
            else:
                # Not enough data yet, output silence and wait
                outdata.fill(0)

    # Start download thread
    download_thread = threading.Thread(target=download_audio, daemon=True)
    download_thread.start()

    # Wait for initial buffer
    print("Buffering initial data...")
    playback_started.wait()

    try:
        # Start audio stream
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=audio_callback,
            blocksize=CHUNK_SIZE
        ):
            # Keep stream alive until done
            while not (download_complete.is_set() and read_position >= len(audio_buffer)):
                time.sleep(0.1)

            # Small delay to let final audio play
            time.sleep(0.5)

        print("\n✓ Success! Real-time streaming playback completed.")

    except Exception as e:
        print(f"✗ Playback error: {str(e)}")

if __name__ == "__main__":
    test_streaming_sounddevice()