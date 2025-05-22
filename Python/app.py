from flask import Flask, jsonify, send_from_directory, request, Response
from flask_cors import CORS
import os, hashlib, datetime, pyodbc
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from DeepTranscript import analyze_audio_with_deepgram
from audio import process_audio_file  
import requests
import logging
import traceback
# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# REMOVE THIS if not needed
frontend_logger = logging.getLogger('frontendLogger')
frontend_logger.setLevel(logging.INFO)
handler = logging.FileHandler('frontend.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
frontend_logger.addHandler(handler)

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
        self.DB_CONN_STR = os.getenv("DB_CONN_STR")  # ODBC connection string in .env

        self.setup_routes()

    def setup_routes(self):
        self.app.route("/audio/<path:filename>", methods=["GET"])(self.serve_audio)
        self.app.route("/azure-audio/<path:filename>", methods=["GET"])(self.get_azure_audio)
        self.app.route("/api/local-files", methods=["GET"])(self.get_local_files)
        self.app.route("/api/azure-files", methods=["GET"])(self.get_azure_files)
        self.app.route("/api/process-audio", methods=["POST"])(self.process_audio_stream)
        self.app.route("/api/log", methods=["POST"])(self.log_from_frontend)
    # def serve_audio(self, filename):
    #     try:
    #         upload_path = os.path.join(UPLOAD_FOLDER, filename)
    #         if os.path.exists(upload_path):
    #             return send_from_directory(UPLOAD_FOLDER, filename)

    #         local_path = os.path.join(self.LOCAL_FOLDER_PATH, filename)
    #         if os.path.exists(local_path):
    #             return send_from_directory(self.LOCAL_FOLDER_PATH, filename)

    #         raise FileNotFoundError(f"File not found: {filename}")
    #     except Exception as e:
    #         logging.error(f"Error serving file '{filename}': {e}\n{traceback.format_exc()}")
    #         return jsonify({"error": str(e)}), 404
    def serve_audio(self, filename):
        try:
            # Check upload folder first
            upload_path = os.path.join(self.UPLOAD_FOLDER, filename)
            if os.path.isfile(upload_path):
                return send_from_directory(self.UPLOAD_FOLDER, filename)

            # Check local folder as fallback
            local_path = os.path.join(self.LOCAL_FOLDER_PATH, filename)
            if os.path.isfile(local_path):
                return send_from_directory(self.LOCAL_FOLDER_PATH, filename)

            # If not found in either path
            error_msg = f"File not found in upload or local folder: {filename}"
            logging.warning(error_msg)
            return jsonify({"error": error_msg}), 404

        except Exception as e:
            logging.error(f"Error serving file '{filename}': {e}\n{traceback.format_exc()}")
            return jsonify({"error": "Internal server error"}), 500
    def get_azure_audio(self, filename):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.AZURE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=self.CONTAINER_NAME, blob=filename)
            stream = blob_client.download_blob()
            audio_data = stream.readall()
            return Response(audio_data, mimetype="audio/mpeg")
        except Exception as e:
            logging.error(f"Error serving Azure audio: {e}\n{traceback.format_exc()}")
            return Response("Audio not found", status=404)

    def get_local_files(self):
        try:
            if not self.LOCAL_FOLDER_PATH or not os.path.exists(self.LOCAL_FOLDER_PATH):
                raise ValueError("LOCAL_FOLDER_PATH is not set or invalid.")
            files = os.listdir(self.LOCAL_FOLDER_PATH)
            audio_files = [f for f in files if f.endswith(".mp3") or f.endswith(".wav")]
            logging.info("Fetched local audio files successfully.")
            return jsonify(audio_files)
        except Exception as e:
            logging.error(f"Error reading local files: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    def get_azure_files(self):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.AZURE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(self.CONTAINER_NAME)
            blobs = container_client.list_blobs()
            audio_files = [blob.name for blob in blobs if blob.name.endswith(".mp3") or blob.name.endswith(".wav")]
            logging.info("Fetched Azure audio files successfully.")
            return jsonify(audio_files)
        except Exception as e:
            logging.error(f"Error fetching Azure files: {e}\n{traceback.format_exc()}")
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
                    logging.info(f"Processing file: {filename} with model: {model}")
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
                    logging.info(f"Uploaded file: {filename}")

                    result = self.run_model(model, filepath)
                    results.append({"filename": filename, "transcription": result["transcription"]})
            logging.info(f"Successfully processed {len(results)} file(s).")
            return jsonify(results)

        except Exception as e:
            logging.error(f"Error in transcription: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    
    def run_model(self, model, filepath):
        filename = os.path.basename(filepath)
        
        model_name = model.lower() if model else "azure"  # default model name
        
        # Set entity_id to 1 by default
        entity_id = 1
        try:    
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
                    logging.info(f"Sending audio to Deepgram: {audio_url}")
                    result = analyze_audio_with_deepgram(audio_url)

                    # ⬇️ Process and insert into DB
                    transcription = result["transcription"]
                    hash_value = hashlib.sha256(transcription.encode()).hexdigest()

                    # ✅ INSERT into DB
                    self.insert_transcription_to_db(entity_id, model_name, filename, hash_value, transcription)
                    print("✅ Deepgram transcription inserted into DB.")

                    return result

                except Exception as e:
                    print("Deepgram ngrok URL error:", str(e))
                    raise

                
            elif model_name == "whisper":
                result = process_audio_file(filepath)
                
            elif model_name == "aws":
                result = process_audio_with_aws(filepath)
                
            elif model_name == "azure":
                result = process_audio_with_azure(filepath)
                
            else:
                raise ValueError("Invalid model selected")

            transcription = result["transcription"]
            hash_value = hashlib.sha256(transcription.encode()).hexdigest()

            # Now insert transcription with entity_id and also model_name
            self.insert_transcription_to_db(entity_id, model_name, filename, hash_value, transcription)
            logging.info(f"Inserted transcription for file: {filename} into database.")
            return result
        except Exception as e:
            logging.error(f"Model processing error: {e}\n{traceback.format_exc()}")
            raise

    def insert_transcription_to_db(self, entity_id, model_name, filename, hash_value, transcription_text):
        try:
            conn = pyodbc.connect(self.DB_CONN_STR)
            cursor = conn.cursor()
            created_at = datetime.datetime.now()
            updated_at = created_at
            cursor.execute("""
                EXEC InsertTranscriptionResult ?, ?, ?, ?, ?, ?, ?
""", (entity_id, model_name, filename, hash_value, transcription_text, created_at, updated_at))

            conn.commit()
            cursor.close()
            conn.close()
            logging.info(f"Database entry complete for: {filename}")
        except Exception as e:
            logging.error(f"Database insertion error: {e}\n{traceback.format_exc()}")

    def log_from_frontend(self):
        try:
            data = request.json
            level = data.get("level", "info").lower()
            message = data.get("message", "")
            metadata = data.get("metadata", {})
            log_msg = f"{message} | Metadata: {metadata}"

            if hasattr(frontend_logger, level):
                getattr(frontend_logger, level)(log_msg)
            else:
                frontend_logger.info(log_msg)

            return jsonify({"status": "logged"}), 200

        except Exception as e:
            print("Error logging from frontend:", str(e))
            return jsonify({"error": str(e)}), 500
    def run(self, port=5000, debug=True):
        self.app.run(port=port, debug=debug)

if __name__ == "__main__":
    server = AudioServerApp()
    server.run()
