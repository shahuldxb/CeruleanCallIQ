import React from "react";

const TranscriptionResult = ({ results }) => {
  if (!results || results.length === 0) {
    return <p>No transcriptions available.</p>;
  }

  return (
    <div className="card p-4 space-y-4  ">
      {results.map((res, idx) => (
        <div key={idx} className="p-4 border rounded bg-gray-100 shadow-sm">
          <p className="font-semibold">File: {res.filename}</p>
          <p>{res.transcription}</p>
        </div>
      ))}
    </div>
  );
};

export default TranscriptionResult;
