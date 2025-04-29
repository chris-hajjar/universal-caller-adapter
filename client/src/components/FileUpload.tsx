import { FC, useState, useCallback, useRef, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';
import { formatFileSize, formatTimeAgo } from '@/lib/utils/formatters';
import { MediaFile } from '@shared/schema';

interface FileUploadProps {
  onFileUploaded: (file: MediaFile) => void;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const ALLOWED_FILE_TYPES = ['audio/mpeg', 'audio/mp3', 'video/mp4'];

const FileUpload: FC<FileUploadProps> = ({ onFileUploaded }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [recentFiles, setRecentFiles] = useState<MediaFile[]>([]);
  const { toast } = useToast();
  const abortControllerRef = useRef<AbortController | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Check file type
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      toast({
        title: 'Invalid file type',
        description: 'Please upload an MP3 or MP4 file.',
        variant: 'destructive',
      });
      return;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      toast({
        title: 'File too large',
        description: 'File size should be less than 100MB.',
        variant: 'destructive',
      });
      return;
    }

    setCurrentFile(file);
    setIsUploading(true);
    setUploadProgress(0);

    // Create FormData
    const formData = new FormData();
    formData.append('file', file);

    try {
      abortControllerRef.current = new AbortController();
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });

      xhr.addEventListener('load', async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText);
          setRecentFiles(prev => [response, ...prev].slice(0, 5));
          onFileUploaded(response);
          toast({
            title: 'Upload Complete',
            description: 'File has been processed successfully.',
          });
        } else {
          toast({
            title: 'Upload Failed',
            description: xhr.responseText || 'An error occurred while processing the file.',
            variant: 'destructive',
          });
        }
        setIsUploading(false);
        setCurrentFile(null);
      });

      xhr.addEventListener('error', () => {
        toast({
          title: 'Upload Failed',
          description: 'Network error occurred.',
          variant: 'destructive',
        });
        setIsUploading(false);
        setCurrentFile(null);
      });

      xhr.open('POST', '/api/media/upload');
      xhr.send(formData);
    } catch (error) {
      toast({
        title: 'Upload Failed',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
      setIsUploading(false);
      setCurrentFile(null);
    }
  }, [onFileUploaded, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/mp3': ['.mp3'],
      'video/mp4': ['.mp4']
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  const cancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsUploading(false);
    setCurrentFile(null);
    toast({
      title: 'Upload Cancelled',
      description: 'File upload has been cancelled.',
    });
  };

  const copyJson = async (mediaFile: MediaFile) => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(mediaFile.specs, null, 2));
      toast({
        title: 'Copied!',
        description: 'JSON data copied to clipboard.',
      });
    } catch (error) {
      toast({
        title: 'Copy Failed',
        description: 'Failed to copy to clipboard.',
        variant: 'destructive',
      });
    }
  };

  const removeFile = (id: number) => {
    setRecentFiles(prev => prev.filter(file => file.id !== id));
    toast({
      description: 'File removed from recent uploads.',
    });
  };

  const selectRecentFile = (mediaFile: MediaFile) => {
    onFileUploaded(mediaFile);
  };

  const dropzoneClasses = useMemo(() => {
    const baseClasses = "border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer transition duration-150";
    if (isDragActive) {
      return `${baseClasses} bg-blue-50 border-blue-300`;
    }
    return `${baseClasses} hover:bg-gray-50`;
  }, [isDragActive]);

  const getUploadStatusText = () => {
    if (uploadProgress < 50) {
      return 'Uploading...';
    } else if (uploadProgress < 85) {
      return 'Processing with FFmpeg...';
    } else {
      return 'Finalizing...';
    }
  };

  return (
    <div className="p-6">
      <div
        {...getRootProps()}
        className={dropzoneClasses}
      >
        <div className="space-y-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-16 w-16 mx-auto text-blue-500"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
            <path d="M12 12v9" />
            <path d="m16 16-4-4-4 4" />
          </svg>
          <div>
            <p className="text-base font-medium text-gray-700">
              Drag &amp; drop your media file here
            </p>
            <p className="text-sm text-gray-500">
              or <span className="text-blue-500 font-medium">browse files</span>
            </p>
          </div>
          <p className="text-xs text-gray-400">
            Supports MP3, MP4 files up to 100MB
          </p>
        </div>
        <input {...getInputProps()} />
      </div>

      {isUploading && (
        <div className="mt-4">
          <div className="flex justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">{currentFile?.name}</span>
            <span className="text-sm font-medium text-gray-700">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-xs text-gray-500">{getUploadStatusText()}</span>
            <button
              className="text-xs text-red-500 hover:text-red-700"
              onClick={cancelUpload}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {recentFiles.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Recent uploads</h3>
          
          {recentFiles.map((file) => (
            <div key={file.id} className="bg-gray-50 rounded p-3 mb-2 flex items-center justify-between">
              <div 
                className="flex items-center cursor-pointer" 
                onClick={() => selectRecentFile(file)}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className={`h-5 w-5 mr-3 ${file.mediaType === 'audio' ? 'text-green-500' : 'text-blue-500'}`}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {file.mediaType === 'audio' ? (
                    <path d="M9 18V5l12-2v13" />
                  ) : (
                    <>
                      <path d="m22 8-6-4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10l6-4V8Z" />
                      <circle cx="9" cy="12" r="1" />
                    </>
                  )}
                </svg>
                <div>
                  <p className="text-sm font-medium text-gray-700">{file.filename}</p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)} • Uploaded {formatTimeAgo(file.createdAt)}
                  </p>
                </div>
              </div>
              <div className="flex">
                <button
                  className="text-gray-400 hover:text-gray-600 mr-2"
                  title="Copy JSON"
                  onClick={() => copyJson(file)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                  </svg>
                </button>
                <button
                  className="text-gray-400 hover:text-gray-600"
                  title="Remove"
                  onClick={() => removeFile(file.id)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M18 6 6 18" />
                    <path d="m6 6 12 12" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="px-0 py-4 mt-4">
        <div className="flex items-center text-xs text-gray-500">
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
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          Files are processed securely and not stored permanently
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
