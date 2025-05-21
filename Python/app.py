from flask import Flask, jsonify, send_from_directory, request, Response
from flask_cors import CORS
import os, json, hashlib
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from DeepTranscript import analyze_audio_with_deepgram
from audio import process_audio_file
import requests

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class AudioServerApp:
    def __init__(self):
        load_dotenv()
        self.app = Flask(__name__)
        CORS(self.app)
        self.AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
        self.CONTAINER_NAME = os.getenv("CONTAINER_NAME")
        self.UPLOAD_FOLDER = os.path.abspath(UPLOAD_FOLDER)
        self.LOCAL_FOLDER_PATH = os.getenv("LOCAL_FOLDER_PATH")
        self.setup_routes()

    def setup_routes(self):
        self.app.route("/audio/<path:filename>", methods=["GET"])(self.serve_audio)
        self.app.route("/azure-audio/<path:filename>", methods=["GET"])(self.get_azure_audio)
        self.app.route("/api/local-files", methods=["GET"])(self.get_local_files)
        self.app.route("/api/azure-files", methods=["GET"])(self.get_azure_files)
        # self.app.route("/process-audio", methods=["POST"])(self.upload_audio_files)
        self.app.route("/api/process-audio", methods=["POST"])(self.process_audio_stream)

    def serve_audio(self, filename):
        try:
            upload_path = os.path.join(self.UPLOAD_FOLDER, filename)
            if os.path.exists(upload_path):
                return send_from_directory(self.UPLOAD_FOLDER, filename)

            local_path = os.path.join(self.LOCAL_FOLDER_PATH, filename)
            if os.path.exists(local_path):
                return send_from_directory(self.LOCAL_FOLDER_PATH, filename)

            raise FileNotFoundError(f"File not found: {filename}")
        except Exception as e:
            print(f"Error serving file '{filename}':", e)
            return jsonify({"error": str(e)}), 404

    def get_azure_audio(self, filename):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.AZURE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=self.CONTAINER_NAME, blob=filename)
            stream = blob_client.download_blob()
            audio_data = stream.readall()
            return Response(audio_data, mimetype="audio/mpeg")
        except Exception as e:
            print("Error serving Azure audio:", e)
            return Response("Audio not found", status=404)

    def get_local_files(self):
        try:
            if not self.LOCAL_FOLDER_PATH or not os.path.exists(self.LOCAL_FOLDER_PATH):
                raise ValueError("LOCAL_FOLDER_PATH is not set or invalid.")
            files = os.listdir(self.LOCAL_FOLDER_PATH)
            audio_files = [f for f in files if f.endswith(".mp3") or f.endswith(".wav")]
            return jsonify(audio_files)
        except Exception as e:
            print("Error reading local files:", str(e))
            return jsonify({"error": str(e)}), 500

    def get_azure_files(self):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.AZURE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(self.CONTAINER_NAME)
            blobs = container_client.list_blobs()
            audio_files = [blob.name for blob in blobs if blob.name.endswith(".mp3") or blob.name.endswith(".wav")]
            return jsonify(audio_files)
        except Exception as e:
            print("Error fetching Azure files:", str(e))
            return jsonify({"error": str(e)}), 500

    def process_audio_stream(self):
        try:
            results = []

            if request.is_json:
                data = request.json
                model = data.get("model")
                filenames = data.get("files", [])
                is_azure = data.get("isAzure", False)

                for filename in filenames:
                    filepath = os.path.join(self.UPLOAD_FOLDER, filename)

                    if is_azure:
                        blob_service_client = BlobServiceClient.from_connection_string(self.AZURE_CONNECTION_STRING)
                        blob_client = blob_service_client.get_blob_client(container=self.CONTAINER_NAME, blob=filename)
                        audio_data = blob_client.download_blob().readall()
                        with open(filepath, "wb") as f:
                            f.write(audio_data)
                    elif os.path.exists(os.path.join(self.LOCAL_FOLDER_PATH, filename)):
                        src_path = os.path.join(self.LOCAL_FOLDER_PATH, filename)
                        with open(src_path, "rb") as src, open(filepath, "wb") as dst:
                            dst.write(src.read())
                    elif os.path.exists(filepath):
                        pass
                    else:
                        raise FileNotFoundError(f"File not found: {filename}")

                    result = self.run_model(model, filepath)
                    results.append({"filename": filename, "transcription": result["transcription"]})
                    os.remove(filepath)

            else:
                model = request.form.get("model")
                files = request.files.getlist("files")

                for file in files:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(self.UPLOAD_FOLDER, filename)
                    file.save(filepath)

                    result = self.run_model(model, filepath)
                    results.append({"filename": filename, "transcription": result["transcription"]})

            return jsonify(results)

        except Exception as e:
            print("Error in transcription:", str(e))
            return jsonify({"error": str(e)}), 500

    def run_model(self, model, filepath):
        if model == "deepgram":
            try:
                NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
                ngrok_response = requests.get(NGROK_API_URL).json()
                public_url = next(
                    (t["public_url"] for t in ngrok_response["tunnels"] if t["public_url"].startswith("https://")),
                    None
                )
                if not public_url:
                    raise Exception("No HTTPS ngrok tunnel found")

                filename = os.path.basename(filepath)
                audio_url = f"{public_url}/audio/{filename}"
                print(f"🔍 Sending this AUDIO_URL to Deepgram: {audio_url}")

                return analyze_audio_with_deepgram(audio_url)
            except Exception as e:
                print("Deepgram ngrok URL error:", str(e))
                raise
        elif model == "whisper":
            return process_audio_file(filepath)
        elif model == "aws":
            return process_audio_with_aws(filepath)
        elif model == "azure":
            return process_audio_with_azure(filepath)
        else:
            raise ValueError("Invalid model selected")

    def run(self, port=5000, debug=True):
        self.app.run(port=port, debug=debug)

if __name__ == "__main__":
    server = AudioServerApp()
    server.run()

