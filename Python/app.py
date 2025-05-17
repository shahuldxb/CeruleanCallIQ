from flask import Flask, jsonify, send_from_directory, request, Response
from flask_cors import CORS
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

class AudioServerApp:
    def __init__(self):
        load_dotenv()
        self.app = Flask(__name__)
        CORS(self.app)

        self.AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
        self.CONTAINER_NAME = os.getenv("CONTAINER_NAME")
        self.LOCAL_FOLDER_PATH = os.getenv("LOCAL_FOLDER_PATH")

        self.setup_routes()

    def setup_routes(self):
        self.app.route("/audio/<path:filename>", methods=["GET"])(self.serve_audio)
        self.app.route("/azure-audio/<path:filename>", methods=["GET"])(self.get_azure_audio)
        self.app.route("/api/local-files", methods=["GET"])(self.get_local_files)
        self.app.route("/api/azure-files", methods=["GET"])(self.get_azure_files)

    def serve_audio(self, filename):
        try:
            if not self.LOCAL_FOLDER_PATH:
                raise ValueError("LOCAL_FOLDER_PATH is not configured.")
            return send_from_directory(self.LOCAL_FOLDER_PATH, filename)
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

    def run(self, port=5000, debug=True):
        self.app.run(port=port, debug=debug)


if __name__ == "__main__":
    server = AudioServerApp()
    server.run()
