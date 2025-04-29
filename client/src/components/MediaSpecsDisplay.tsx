import { FC, useState } from 'react';
import { MediaFile } from '@shared/schema';
import { formatFileSize, formatDuration } from '@/lib/utils/formatters';
import { useToast } from '@/hooks/use-toast';
import BitrateModifier from './BitrateModifier';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface MediaSpecsDisplayProps {
  mediaFile: MediaFile | null;
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
}

type TabType = 'video' | 'audio' | 'json';

const MediaSpecsDisplay: FC<MediaSpecsDisplayProps> = ({
  mediaFile,
  isLoading,
  hasError,
  onRetry,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('video');
  const { toast } = useToast();

  const copyJson = async () => {
    if (!mediaFile) return;
    
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

  const downloadJson = () => {
    if (!mediaFile) return;
    
    const jsonString = JSON.stringify(mediaFile.specs, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${mediaFile.filename.split('.')[0]}_specs.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="p-6 h-full flex flex-col">
        <div className="flex-grow flex flex-col items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-500 text-sm">Processing media file...</p>
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="p-6 h-full flex flex-col">
        <div className="flex-grow flex flex-col items-center justify-center py-12">
          <div className="bg-red-100 text-red-700 p-4 rounded-lg max-w-md text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8 mx-auto mb-2"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <h3 className="font-medium mb-1">Processing Failed</h3>
            <p className="text-sm">We couldn't process this file. Please ensure it's a valid MP3 or MP4 file and try again.</p>
            <button
              className="mt-3 bg-red-500 hover:bg-red-600 text-white py-1 px-4 rounded text-sm transition duration-150"
              onClick={onRetry}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!mediaFile) {
    return (
      <div className="p-6 h-full flex flex-col">
        <div className="flex-grow flex flex-col items-center justify-center py-12">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-12 w-12 text-gray-400 mb-4"
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
          <p className="text-gray-500 text-lg font-medium mb-1">No Media File Selected</p>
          <p className="text-gray-400 text-sm text-center">
            Upload an MP3 or MP4 file to see its specifications
          </p>
        </div>
      </div>
    );
  }

  // Extract specifications
  const specs = mediaFile.specs;
  const format = specs.format || {};
  const videoStream = specs.streams?.find(s => s.codec_type === 'video');
  const audioStream = specs.streams?.find(s => s.codec_type === 'audio');
  
  // Calculate additional properties
  const resolution = videoStream ? `${videoStream.width} × ${videoStream.height}` : 'N/A';
  const duration = format.duration ? formatDuration(parseFloat(format.duration)) : 'N/A';
  const fileType = mediaFile.mediaType === 'audio' ? 'MP3 Audio' : 'MP4 Video';

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex-grow">
        {/* Summary view */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Summary</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                      Type
                      <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      The file format type. MP3 is an audio-only format, while MP4 is a container format 
                      that can include video, audio, subtitles, and other data.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <p className="text-sm font-medium text-gray-800">{fileType}</p>
            </div>
            <div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                      File Size
                      <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      The total size of the media file in bytes, kilobytes (KB), megabytes (MB), or gigabytes (GB).
                      File size depends on duration, resolution, and encoding quality.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <p className="text-sm font-medium text-gray-800">{formatFileSize(mediaFile.size)}</p>
            </div>
            <div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                      Duration
                      <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                    </p>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      The total playback time of the media file, displayed in hours:minutes:seconds format.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <p className="text-sm font-medium text-gray-800">{duration}</p>
            </div>
            {videoStream && (
              <div>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                        Resolution
                        <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                      </p>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs max-w-xs">
                        The number of pixels in each dimension (width × height). Common resolutions include 
                        1920×1080 (Full HD), 3840×2160 (4K), and 7680×4320 (8K).
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <p className="text-sm font-medium text-gray-800">{resolution}</p>
              </div>
            )}
          </div>
        </div>
        
        {/* Tabs for different spec sections */}
        <div className="mb-4 border-b border-gray-200">
          <ul className="flex -mb-px" role="tablist">
            <li className="mr-1">
              <button
                className={`py-2 px-4 text-sm font-medium ${
                  activeTab === 'video'
                    ? 'text-blue-600 border-b-2 border-blue-500'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                role="tab"
                aria-selected={activeTab === 'video'}
                onClick={() => setActiveTab('video')}
              >
                Video
              </button>
            </li>
            <li className="mr-1">
              <button
                className={`py-2 px-4 text-sm font-medium ${
                  activeTab === 'audio'
                    ? 'text-blue-600 border-b-2 border-blue-500'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                role="tab"
                aria-selected={activeTab === 'audio'}
                onClick={() => setActiveTab('audio')}
              >
                Audio
              </button>
            </li>
            <li>
              <button
                className={`py-2 px-4 text-sm font-medium ${
                  activeTab === 'json'
                    ? 'text-blue-600 border-b-2 border-blue-500'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                role="tab"
                aria-selected={activeTab === 'json'}
                onClick={() => setActiveTab('json')}
              >
                Raw JSON
              </button>
            </li>
          </ul>
        </div>
        
        {/* Tab content */}
        <div className="tab-content">
          {/* Video tab */}
          <div 
            className={activeTab === 'video' ? 'block' : 'hidden'} 
            role="tabpanel"
          >
            {!videoStream ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No video stream found in this file.</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Codec
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            A codec is software or hardware that compresses and decompresses digital video. 
                            Common video codecs include H.264, H.265 (HEVC), VP9, and AV1.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.codec_long_name || videoStream.codec_name || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Frame Rate
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Frame rate is the number of images displayed per second in a video. 
                            Higher frame rates (e.g., 60fps) create smoother motion. Standard film typically uses 24fps.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.r_frame_rate 
                        ? parseFloat(eval(videoStream.r_frame_rate).toFixed(2)) + ' fps'
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Bitrate
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Bitrate is the amount of data processed per second. Higher bitrates usually mean 
                            better quality video but larger file sizes. Measured in Mbps (megabits per second).
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.bit_rate 
                        ? (parseInt(videoStream.bit_rate) / 1000000).toFixed(2) + ' Mbps'
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Pixel Format
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Pixel format determines how color and transparency information is stored for each pixel.
                            Common formats include RGB, YUV, and their variants with different bit depths and subsampling.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.pix_fmt || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Color Space
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Color space defines the range of colors in a video. Different color spaces (BT.709, BT.2020, etc.) 
                            support different color ranges and are used for different display technologies.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.color_space || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Aspect Ratio
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Aspect ratio is the proportional relationship between a video's width and height.
                            Common aspect ratios include 16:9 (widescreen), 4:3 (standard), and 21:9 (ultrawide).
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {videoStream.display_aspect_ratio || 'N/A'}
                    </p>
                  </div>
                </div>
                
                {/* Bitrate Modifier Component */}
                <BitrateModifier mediaFile={mediaFile} activeTab="video" />
              </>
            )}
          </div>
          
          {/* Audio tab */}
          <div 
            className={activeTab === 'audio' ? 'block' : 'hidden'} 
            role="tabpanel"
          >
            {!audioStream ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No audio stream found in this file.</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Codec
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            An audio codec compresses and decompresses digital audio. Common audio codecs include 
                            MP3, AAC, FLAC, and Opus. Different codecs offer different trade-offs between quality and file size.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.codec_long_name || audioStream.codec_name || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Sample Rate
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Sample rate is the number of audio samples taken per second, measured in Hertz (Hz).
                            Common rates are 44.1kHz (CD quality), 48kHz (standard for digital video), and 96kHz (high-resolution audio).
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.sample_rate ? `${audioStream.sample_rate} Hz` : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Channels
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Audio channels determine how many independent audio signals are used. 
                            Mono (1) uses one channel, stereo (2) uses two, while surround sound may use 5.1, 7.1, or more channels.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.channels 
                        ? `${audioStream.channels} (${audioStream.channels === 1 ? 'Mono' : 'Stereo'})`
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Bitrate
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Audio bitrate is the amount of data processed per second, measured in kilobits per second (kbps).
                            Higher bitrates mean better quality audio. Common values: 128kbps (standard), 320kbps (high quality).
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.bit_rate 
                        ? (parseInt(audioStream.bit_rate) / 1000) + ' kbps'
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Channel Layout
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Channel layout describes how audio channels are arranged (e.g., "stereo," "5.1"). 
                            This determines the spatial positioning of sound in playback systems.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.channel_layout || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-gray-500 cursor-help inline-flex items-center">
                            Language
                            <span className="ml-1 inline-block w-3.5 h-3.5 rounded-full bg-gray-100 text-gray-500 text-[10px] flex items-center justify-center">?</span>
                          </p>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            The language tag indicates the spoken language in the audio track.
                            This is important for multi-language content and accessibility.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <p className="text-sm font-medium text-gray-800">
                      {audioStream.tags?.language || 'N/A'}
                    </p>
                  </div>
                </div>
                
                {/* Bitrate Modifier Component */}
                <BitrateModifier mediaFile={mediaFile} activeTab="audio" />
              </>
            )}
          </div>
          
          {/* JSON tab */}
          <div 
            className={activeTab === 'json' ? 'block' : 'hidden'}
            role="tabpanel"
          >
            <div className="bg-gray-800 rounded-md p-4 overflow-x-auto max-h-96 font-mono text-xs">
              <pre className="text-white">
                {/* Format the JSON with syntax highlighting */}
                {JSON.stringify(specs, null, 2)
                  .replace(/"([^"]+)":/g, '<span class="text-amber-400">"$1"</span>:')
                  .replace(/"([^"]+)"/g, '<span class="text-emerald-400">"$1"</span>')
                  .replace(/\b(true|false|null)\b/g, '<span class="text-violet-400">$1</span>')
                  .replace(/\b(\d+(\.\d+)?)\b/g, '<span class="text-blue-400">$1</span>')}
              </pre>
            </div>
            <div className="mt-2 flex justify-end">
              <button
                className="inline-flex items-center px-3 py-1 text-xs font-medium text-blue-600 bg-blue-100 rounded hover:bg-blue-200 transition duration-150"
                onClick={copyJson}
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
                  <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                </svg>
                Copy JSON
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MediaSpecsDisplay;