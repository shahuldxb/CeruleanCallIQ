import React from "react";

interface TranscriptionItem {
  filename: string;
  transcription: string;
}

interface TranscriptionResultProps {
  results: TranscriptionItem[];
}
const TranscriptionResult: React.FC<TranscriptionResultProps> = ({
  results,
}) => {
  if (!results || results.length === 0) {
    return <p className="dark:text-gray-800">No transcriptions available.</p>;
  }

  return (
    <div className="card p-4 space-y-4  ">
      {results.map((res) => (
        <div
          key={res.filename}
          className="p-4 border rounded bg-gray-100 dark:bg-gray-200 shadow-sm"
        >
          <p className="dark:text-gray-800 font-semibold pb-4">
            <span className="border-b-2 border-gray-400 pb-2">
              FileName: {res.filename}
            </span>
          </p>
          <p className="dark:text-gray-800">{res.transcription}</p>
        </div>
      ))}
    </div>
  );
};

export default TranscriptionResult;
