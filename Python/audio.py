import whisper
import traceback

transcribe_model = whisper.load_model("base")
# translate_model = whisper.load_model("medium")

def process_audio_file(file_path):
    print(f"Processing file: {file_path}")
    
    # Transcription
    try:
        print("Transcribing...")
        transcription_result = transcribe_model.transcribe(file_path)
        transcription_text = transcription_result["text"]
        print('Transcription:', transcription_text)
    except Exception as e:
        print("Transcription error:", str(e))
        traceback.print_exc()
        transcription_text = "Error transcribing audio."

    # # Translation
    # try:
    #     print("Translating...")
    #     translation_result = translate_model.transcribe(file_path, task="translate")
    #     translation_text = translation_result["text"]
    #     print("Translation:", translation_text)
    # except Exception as e:
    #     print("Translation error:", str(e))
    #     traceback.print_exc()
    #     translation_text = "Error translating audio."

    return {
        "transcription": transcription_text,
        # "translation": translation_text
    }
