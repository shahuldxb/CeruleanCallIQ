import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const Transcription: React.FC = () => {
  const [selectOption, setSelectOption] = useState<string>("");
  const [files, setFiles] = useState<{ file: string; isAzure: boolean }[]>([]);
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);

  const options = [
    { label: "azure", value: "1" },
    { label: "localFolder", value: "2" },
    { label: "Aws", value: "3" },
    { label: "Browse File", value: "4" },
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

  return (
    <div className="card p-4">
      <div className="flex items-center gap-4 flex-wrap">
        {options.map((Option) => (
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
        ))}
        <div className="ml-auto">
          <button type="button" className="btn btn-primary btn-outline">
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

      <div className="grid grid-cols-2 mt-4 gap-4 max-h-[700px] ">
        <div className="border p-2">
          <h1 className="text-center  border-b p-2">Inbox</h1>
        <div className=" p-2 scrollable scrollbar-hide max-h-[620px]">
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
                    // Pause Icon
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
                    // Play Icon
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

        <div className="border p-2">
          <h1 className="text-center border-b p-2">Outbox</h1>
           <div className=" p-2 scrollable scrollbar-hide max-h-[620px]">
          </div>
        </div>
      </div>
    </div>
  );
};

export default Transcription;
