import { FC, useState } from 'react';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import FileUpload from '@/components/FileUpload';
import MediaSpecsDisplay from '@/components/MediaSpecsDisplay';
import APISection from '@/components/APISection';
import { MediaFile } from '@shared/schema';

const Home: FC = () => {
  const [selectedFile, setSelectedFile] = useState<MediaFile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleFileUploaded = (file: MediaFile) => {
    setSelectedFile(file);
    setIsLoading(false);
    setHasError(false);
  };

  const handleRetry = () => {
    setHasError(false);
    setSelectedFile(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="col-span-1">
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Upload Media File</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Drag and drop an MP3 or MP4 file to extract its specifications
                </p>
              </div>
              
              <FileUpload onFileUploaded={handleFileUploaded} />
            </div>

            <APISection />
          </div>

          <div className="col-span-1">
            <div className="bg-white rounded-lg shadow h-full overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-medium text-gray-800">Media Specifications</h2>
                  
                  {selectedFile && (
                    <div className="flex items-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className={`h-5 w-5 mr-2 ${selectedFile.mediaType === 'audio' ? 'text-green-500' : 'text-blue-500'}`}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        {selectedFile.mediaType === 'audio' ? (
                          <path d="M9 18V5l12-2v13" />
                        ) : (
                          <>
                            <path d="m22 8-6-4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10l6-4V8Z" />
                            <circle cx="9" cy="12" r="1" />
                          </>
                        )}
                      </svg>
                      <span className="text-sm font-medium text-gray-600">
                        {selectedFile.filename}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              <MediaSpecsDisplay
                mediaFile={selectedFile}
                isLoading={isLoading}
                hasError={hasError}
                onRetry={handleRetry}
              />
              
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Processed with FFmpeg</span>
                  {selectedFile && (
                    <div>
                      <button
                        className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition duration-150"
                        onClick={() => {
                          const jsonString = JSON.stringify(selectedFile.specs, null, 2);
                          const blob = new Blob([jsonString], { type: 'application/json' });
                          const url = URL.createObjectURL(blob);
                          
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${selectedFile.filename.split('.')[0]}_specs.json`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);
                        }}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-4 w-4 mr-1"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        Download JSON
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Home;
