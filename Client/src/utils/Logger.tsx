const BASE_URL: string = import.meta.env.VITE_APP_API_URL;
const API_URL = `${BASE_URL}/api/log`;

console.log("Base URL:", BASE_URL);


// Define log levels
type LogLevel = 'log' | 'info' | 'warn' | 'error' | 'debug';

// Define metadata type
interface LogMetadata {
  [key: string]: unknown;
}

// Define the logging function
export const logFrontend = async (
  level: LogLevel,
  message: string,
  metadata: LogMetadata = {}
): Promise<void> => {
  const payload = {
    level,
    message,
    metadata,
    timestamp: new Date().toISOString(),
  };

  // Log to console in dev
  if (import.meta.env.MODE !== 'production') {
    console[level](`[${level.toUpperCase()}]: ${message}`, metadata);
  }

  // Send to backend
  try {
    await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.error('Failed to send log to server:', err);
  }
};
