import { FC } from 'react';

const APISection: FC = () => {
  return (
    <div className="mt-6 bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-800">API Integration</h2>
        <p className="mt-1 text-sm text-gray-500">
          Use our API to integrate media specifications extraction
        </p>
      </div>
      <div className="p-6">
        <div className="bg-gray-800 rounded-md p-4 overflow-x-auto">
          <pre className="text-xs text-gray-300 font-mono"><code>curl -X POST \
  http://localhost:5000/api/media/upload \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/file.mp4'</code></pre>
        </div>
        <div className="mt-4">
          <a 
            href="https://ffmpeg.org/documentation.html" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-sm text-blue-500 hover:text-blue-700 font-medium"
          >
            View full API documentation <span className="text-xs">→</span>
          </a>
        </div>
      </div>
    </div>
  );
};

export default APISection;
