import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import TranscriptionResult from "./TranscriptionResult";
import { logFrontend } from "../../utils/Logger";
interface FileItem {
  file: string;
  isAzure: boolean;
  rawFile?: File;
}

const Transcription: React.FC = () => {
  const [selectOption, setSelectOption] = useState<string>("");
  const [selectModelOption, setSelectModelOption] = useState<string>("");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);
  const [showResult, setShowResult] = useState(false);
  const [transcriptionResults, setTranscriptionResults] = useState<
    { filename: string; transcription: string }[]
  >([]);

  const [outboxFiles, setOutboxFiles] = useState<string[]>([]);
  const options = [
    { label: "azure", value: "1" },
    { label: "localFolder", value: "2" },
    { label: "Aws", value: "3" },
    { label: "Browse File", value: "4" },
  ];
  const Modeloptions = [
    { label: "azure", value: "azure" },
    { label: "Deepgram", value: "deepgram" },
    { label: "Aws", value: "aws" },
    { label: "Whisper", value: "whisper" },
  ];

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        if (selectOption === "1") {
          const res = await axios.get("http://localhost:5000/api/azure-files");
          const azureFiles = res.data.map((file: string) => ({
            file,
            isAzure: true,
          }));
          setFiles(azureFiles);
        } else if (selectOption === "2") {
          const res = await axios.get("http://localhost:5000/api/local-files");
          const localFiles = res.data.map((file: string) => ({
            file,
            isAzure: false,
          }));
          setFiles(localFiles);
        } else if (selectOption === "4") {
          document.getElementById("file-picker")?.click();
        } else {
          setFiles([]);
        }
      } catch (err) {
        console.error("Error fetching files", err);
      }
    };

    fetchFiles();
  }, [selectOption]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      const names = Array.from(selectedFiles).map((f) => ({
        file: f.name,
        rawFile: f, // 🛠️ Store the actual File object
        isAzure: false,
      }));
      setFiles(names);
    }
  };

  const togglePlayPause = (index: number) => {
    const currentAudio = audioRefs.current[index];
    if (!currentAudio) return;

    audioRefs.current.forEach((audio, i) => {
      if (i !== index && audio) {
        audio.pause();
        audio.currentTime = 0;
      }
    });

    if (playingIndex === index) {
      currentAudio.pause();
      setPlayingIndex(null);
    } else {
      currentAudio.play();
      setPlayingIndex(index);
    }
  };
  useEffect(() => {
    console.log("Updated transcriptionResults:", transcriptionResults);
  }, [transcriptionResults]);

  const handleProcess = async () => {
    if (!selectModelOption || files.length === 0) {
      alert("Please select a model and at least one file.");
      return;
    }
    logFrontend("info", "user clicked the process button", {
      page: "transcription page",
    });
    const isBrowse = selectOption === "4";

    try {
      let remainingFiles = [...files];
      const allResults = [];

      if (isBrowse) {
        for (const fileObj of files) {
          if (!fileObj.rawFile) continue;

          const formData = new FormData();
          formData.append("model", selectModelOption);
          formData.append("files", fileObj.rawFile);

          const response = await axios.post(
            "http://localhost:5000/api/process-audio",
            formData,
            {
              headers: { "Content-Type": "multipart/form-data" },
            }
          );

          const resultArray = response.data;
          if (Array.isArray(resultArray)) {
            allResults.push(...resultArray);
          }

          setOutboxFiles((prev) => [...prev, fileObj.file]);
          remainingFiles = remainingFiles.filter(
            (f) => f.file !== fileObj.file
          );
          setFiles(remainingFiles); // update inbox immediately
          setTranscriptionResults((prev) => [...prev, ...resultArray]);
        }
      } else {
        // Handle other options: one file at a time
        for (const fileObj of files) {
          const response = await axios.post(
            "http://localhost:5000/api/process-audio",
            {
              model: selectModelOption,
              files: [fileObj.file],
              isAzure: selectOption === "1",
            }
          );

          const resultArray = response.data;
          if (Array.isArray(resultArray)) {
            allResults.push(...resultArray);
          }

          setOutboxFiles((prev) => [...prev, fileObj.file]);
          remainingFiles = remainingFiles.filter(
            (f) => f.file !== fileObj.file
          );
          setFiles(remainingFiles); // update inbox immediately
          setTranscriptionResults((prev) => [...prev, ...resultArray]);
        }
      }
    } catch (err) {
      console.error("Error processing audio:", err);
      logFrontend("error", "Error processing audio", {
        error: err instanceof Error ? err.message : String(err),
        model: selectModelOption,
        source: selectOption,
        page: "transcription page",
      });
      alert("An error occurred during processing.");
    }
  };

  return (
    <div className="card p-4 ">
      <div className="flex items-center gap-4 flex-wrap pb-2">
        <h1 className=" text-md whitespace-nowrap">Select Folder :</h1>

        {options.map((Option) => (
          <>
            <div className="flex items-center gap-2" key={Option.value}>
              <input
                className="checkbox"
                id={`check-${Option.value}`}
                type="checkbox"
                checked={selectOption === Option.value}
                onChange={() =>
                  setSelectOption((pre) =>
                    pre === Option.value ? "" : Option.value
                  )
                }
              />
              <label
                className="label form-label"
                htmlFor={`check-${Option.value}`}
              >
                {Option.label}
              </label>
            </div>
          </>
        ))}
        <div className="ml-auto">
          <button
            type="button"
            className="btn btn-primary btn-outline"
            onClick={handleProcess}
          >
            Process
          </button>
        </div>
        <input
          type="file"
          id="file-picker"
          accept="audio/*"
          multiple
          style={{ display: "none" }}
          onChange={handleFileSelect}
        />
      </div>
      <div className="flex items-center gap-4 flex-wrap pb-2">
        <h1 className="text-md whitespace-nowrap ">Select Model :</h1>
        {Modeloptions.map((Option) => (
          <div className="flex items-center gap-2" key={Option.value}>
            <input
              className="checkbox"
              id={`check-${Option.value}`}
              type="checkbox"
              checked={selectModelOption === Option.value}
              onChange={() =>
                setSelectModelOption((pre) =>
                  pre === Option.value ? "" : Option.value
                )
              }
            />
            <label
              className="label form-label"
              htmlFor={`check-${Option.value}`}
            >
              {Option.label}
            </label>
          </div>
        ))}
      </div>
      {!showResult ? (
        <>
          <div className="grid grid-cols-2 mt-4 gap-4 h-[550px] ">
            <div className="border p-2 dark:text-gray-700">
              <h1 className="text-center  border-b p-2 ">Inbox</h1>
              <div className=" p-2 scrollable scrollbar-hide h-[500px]">
                <ul className="space-y-3">
                  {files.map(({ file, isAzure }, idx) => (
                    <li
                      key={idx}
                      className="flex items-center justify-between gap-2 border-b pb-3 pt-3"
                    >
                      <div className="flex-1 text-left">
                        {idx}: {file}
                      </div>
                      <div
                        className="cursor-pointer"
                        onClick={() => togglePlayPause(idx)}
                      >
                        {playingIndex === idx ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="24px"
                            height="24px"
                            viewBox="0 0 24 24"
                            version="1.1"
                          >
                            <title>Pause</title>
                            <desc>Created with Sketch.</desc>
                            <g
                              stroke="none"
                              strokeWidth="1"
                              fill="none"
                              fillRule="evenodd"
                            >
                              <rect x="0" y="0" width="24" height="24" />
                              <path
                                d="M8,6 L10,6 C10.5522847,6 11,6.44771525 11,7 L11,17 C11,17.5522847 10.5522847,18 10,18 L8,18 C7.44771525,18 7,17.5522847 7,17 L7,7 C7,6.44771525 7.44771525,6 8,6 Z M14,6 L16,6 C16.5522847,6 17,6.44771525 17,7 L17,17 C17,17.5522847 16.5522847,18 16,18 L14,18 C13.4477153,18 13,17.5522847 13,17 L13,7 C13,6.44771525 13.4477153,6 14,6 Z"
                                fill="#3391F2"
                              />
                            </g>
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="24px"
                            height="24px"
                            viewBox="0 0 24 24"
                            version="1.1"
                          >
                            <title>Play</title>
                            <desc>Created with Sketch.</desc>
                            <g
                              stroke="none"
                              strokeWidth="1"
                              fill="none"
                              fillRule="evenodd"
                            >
                              <rect x="0" y="0" width="24" height="24" />
                              <path
                                d="M9.82866499,18.2771971 L16.5693679,12.3976203 C16.7774696,12.2161036 16.7990211,11.9002555 16.6175044,11.6921539 C16.6029128,11.6754252 16.5872233,11.6596867 16.5705402,11.6450431 L9.82983723,5.72838979 C9.62230202,5.54622572 9.30638833,5.56679309 9.12422426,5.7743283 C9.04415337,5.86555116 9,5.98278612 9,6.10416552 L9,17.9003957 C9,18.1765381 9.22385763,18.4003957 9.5,18.4003957 C9.62084305,18.4003957 9.73759731,18.3566309 9.82866499,18.2771971 Z"
                                fill="#3391F2"
                              />
                            </g>
                          </svg>
                        )}
                      </div>
                      <audio
                        ref={(el) => (audioRefs.current[idx] = el)}
                        src={`http://localhost:5000/${
                          isAzure ? "azure-audio" : "audio"
                        }/${file}`}
                        onEnded={() => setPlayingIndex(null)}
                        onError={() => console.error(`Error loading ${file}`)}
                      />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="border p-2 dark:text-gray-700">
              <h1 className="text-center border-b p-2 ">Outbox</h1>
              <div className="p-2 scrollable scrollbar-hide h-[520px]">
                <ul className="space-y-3">
                  {outboxFiles.map((file, idx) => (
                    <li key={idx} className="border-b pb-3 pt-3">
                      {file}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="mt-6 scrollable scrollbar-hide h-[550px]">
          <h2 className="text-lg font-semibold mb-4">Transcription Result</h2>
          <TranscriptionResult results={transcriptionResults} />
        </div>
      )}
      <p
        onClick={() => setShowResult(!showResult)}
        className="pt-10 ml-auto text-blue-500 hover:underline cursor-pointer flex items-center gap-1"
      >
        {showResult ? (
          <>
            <i className="ki-filled ki-arrow-left "></i>Go Back
          </>
        ) : (
          <>
            view result <i className="ki-filled ki-arrow-right"></i>
          </>
        )}
      </p>
    </div>
  );
};

export default Transcription;
