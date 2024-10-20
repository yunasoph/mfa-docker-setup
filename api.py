from flask import Flask, request, jsonify
import os
import subprocess
import requests

app = Flask(__name__)

UPLOAD_FOLDER = '/workspaces/mfa-docker-setup/uploads'
OUTPUT_FOLDER = '/workspaces/mfa-docker-setup/aligned_output'
CMUDICT_PATH = '/workspaces/mfa-docker-setup/cmudict.dict'

# Create upload and output folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Automatically download the CMU dictionary if not already present
if not os.path.exists(CMUDICT_PATH):
    cmudict_url = 'https://raw.githubusercontent.com/MontrealCorpusTools/mfa-models/main/dictionary/english/cmudict.dict'
    response = requests.get(cmudict_url)
    if response.status_code == 200:
        with open(CMUDICT_PATH, 'w') as f:
            f.write(response.text)
    else:
        raise RuntimeError("Could not download CMU dictionary")

@app.route('/upload', methods=['POST'])
def upload_files():
    # Ensure both audio and transcription files are provided in the request
    if 'audio' not in request.files or 'transcription' not in request.files:
        return jsonify({"error": "Please upload both 'audio' and 'transcription' files"}), 400

    audio = request.files['audio']
    transcription = request.files['transcription']

    # Save uploaded files
    audio_path = os.path.join(UPLOAD_FOLDER, audio.filename)
    transcription_path = os.path.join(UPLOAD_FOLDER, transcription.filename)
    audio.save(audio_path)
    transcription.save(transcription_path)

    # Run Montreal Forced Aligner using Docker
    try:
        subprocess.run([
            'docker', 'run', '--rm',
            '-v', f'{UPLOAD_FOLDER}:/app/audio_files',
            '-v', f'{OUTPUT_FOLDER}:/app/output',
            'mmcauliffe/montreal-forced-aligner:latest',
            'align', '/app/audio_files', CMUDICT_PATH, 'english', '/app/output'
        ], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error during alignment: {e}"}), 500

    # Check for output
    aligned_file = os.path.join(OUTPUT_FOLDER, audio.filename.replace('.wav', '.TextGrid'))
    if os.path.exists(aligned_file):
        return jsonify({"message": "Alignment completed", "output_file": aligned_file})
    else:
        return jsonify({"error": "Alignment file not found"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
