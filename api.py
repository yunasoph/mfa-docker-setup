from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

# Set the maximum upload size to 100 MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

UPLOAD_FOLDER = '/workspaces/mfa-docker-setup/uploads'
OUTPUT_FOLDER = '/workspaces/mfa-docker-setup/aligned_output'

# Create upload and output folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File size is too large. Maximum allowed size is 100 MB."}), 413

@app.route('/upload', methods=['POST'])
def upload_files():
    # Ensure audio, transcription, and dictionary files are provided in the request
    if 'audio' not in request.files or 'transcription' not in request.files or 'dictionary' not in request.files:
        return jsonify({"error": "Please upload 'audio', 'transcription', and 'dictionary' files"}), 400

    audio = request.files['audio']
    transcription = request.files['transcription']
    dictionary = request.files['dictionary']

    # Save uploaded files
    audio_path = os.path.join(UPLOAD_FOLDER, audio.filename)
    transcription_path = os.path.join(UPLOAD_FOLDER, transcription.filename)
    dictionary_path = os.path.join(UPLOAD_FOLDER, dictionary.filename)

    audio.save(audio_path)
    transcription.save(transcription_path)
    dictionary.save(dictionary_path)

    # Run Montreal Forced Aligner using Docker
    try:
        subprocess.run([
            'docker', 'run', '--rm',
            '-v', f'{UPLOAD_FOLDER}:/app/audio_files',
            '-v', f'{OUTPUT_FOLDER}:/app/output',
            'mmcauliffe/montreal-forced-aligner:latest',
            'align', '/app/audio_files', dictionary_path, 'english', '/app/output'
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
