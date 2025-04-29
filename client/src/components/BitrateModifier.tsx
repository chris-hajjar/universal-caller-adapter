import React, { FC, useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { MediaFile, bitrateFormatSchema } from '@shared/schema';
import { useToast } from '@/hooks/use-toast';
import { queryClient, apiRequest } from '@/lib/queryClient';
import { formatFileSize } from '@/lib/utils/formatters';
import { Button } from '@/components/ui/button';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface BitrateModifierProps {
  mediaFile: MediaFile;
  activeTab: 'video' | 'audio';
}

// Form schema
const formSchema = z.object({
  targetBitrate: bitrateFormatSchema,
});

type FormValues = z.infer<typeof formSchema>;

const BitrateModifier: FC<BitrateModifierProps> = ({ mediaFile, activeTab }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();
  
  // Real progress tracking from server
  useEffect(() => {
    // Clean up any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    if (isProcessing && jobId) {
      // Start a new interval to check encoding progress
      progressIntervalRef.current = setInterval(async () => {
        try {
          const response = await fetch(`/api/media/progress/${jobId}`);
          if (response.ok) {
            const data = await response.json();
            if (data?.status === 'success') {
              setProgress(data.data?.progress || 0);
              
              // If progress is 100%, encoding is complete
              if (data.data?.progress === 100) {
                checkReEncodingStatus();
              }
            }
          }
        } catch (error) {
          console.error('Error fetching encoding progress:', error);
        }
      }, 1000);
    } else if (isComplete) {
      setProgress(100);
    }
    
    // Cleanup function
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [isProcessing, isComplete, jobId]);

  // Poll for re-encoding status
  const checkReEncodingStatus = async () => {
    try {
      const response = await fetch(`/api/media/${mediaFile.id}/status`);
      if (response.ok) {
        const data = await response.json();
        
        if (data.status === 'success' && data.data.isReEncoded) {
          // Re-encoding is complete
          clearInterval(progressIntervalRef.current!);
          progressIntervalRef.current = null;
          
          // Update UI and cached data
          setIsProcessing(false);
          setIsComplete(true);
          
          // Update cached media file data
          queryClient.invalidateQueries({ queryKey: ['/api/media', mediaFile.id] });
          
          toast({
            title: 'Re-encoding Complete',
            description: 'Your media file has been successfully re-encoded.',
          });
        }
      }
    } catch (error) {
      console.error('Error checking re-encoding status:', error);
    }
  };

  // Set up the form
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      targetBitrate: '',
    },
  });

  const onSubmit = async (data: FormValues) => {
    setIsProcessing(true);
    setProgress(0);
    try {
      const payload = {
        mediaFileId: mediaFile.id,
        targetBitrate: data.targetBitrate,
        streamType: activeTab, // Pass the active tab to specify which stream type to modify
      };
      
      const result = await apiRequest('POST', '/api/media/reencode', payload);

      // The API now returns a 202 status with a jobId
      if (result && typeof result === 'object' && 'status' in result && 
          result.status === 'processing' && 
          'data' in result && 
          result.data && 
          typeof result.data === 'object' && 
          'jobId' in result.data) {
        
        setJobId(result.data.jobId as string);
        
        toast({
          title: 'Re-encoding Started',
          description: 'Your media file is being re-encoded. You can track the progress.',
        });
      } else {
        // Handle immediate completion (unlikely with large files)
        setIsComplete(true);
        setIsProcessing(false);
        
        // Update cached media file data
        queryClient.invalidateQueries({ queryKey: ['/api/media', mediaFile.id] });
        
        toast({
          title: 'Re-encoding Complete',
          description: 'Your media file has been successfully re-encoded.',
        });
      }
    } catch (error) {
      setIsProcessing(false);
      setJobId(null);
      
      let errorMessage = 'Failed to re-encode the media file';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast({
        title: 'Re-encoding Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const handleDownload = async () => {
    try {
      // First check if the file is available for download
      const statusResponse = await fetch(`/api/media/${mediaFile.id}/status`);
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        
        if (statusData && 
            typeof statusData === 'object' && 
            'data' in statusData && 
            statusData.data && 
            typeof statusData.data === 'object' && 
            'fileExists' in statusData.data && 
            !statusData.data.fileExists) {
          throw new Error('Re-encoded file is not available. It may have been deleted.');
        }
      }
      
      // Create a download URL from the API endpoint
      const downloadUrl = `/api/media/${mediaFile.id}/download`;
      
      // Create a link and trigger download
      const a = document.createElement('a');
      a.href = downloadUrl;
      
      // Create safer filename
      const baseFilename = mediaFile.filename.split('.')[0] || 'file';
      const extension = mediaFile.filename.lastIndexOf('.') > 0 
        ? mediaFile.filename.substring(mediaFile.filename.lastIndexOf('.')) 
        : '.mp4';
      
      a.download = `${baseFilename}_reencoded_${mediaFile.reEncodedBitrate || 'modified'}${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      toast({
        title: 'Download Started',
        description: 'Your re-encoded file is being downloaded.',
      });
    } catch (error) {
      let errorMessage = 'Failed to download the re-encoded file';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast({
        title: 'Download Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Modify Bitrate</h3>
      
      {mediaFile.isReEncoded ? (
        <div className="space-y-4">
          <div className="bg-green-50 text-green-800 p-3 rounded-md text-sm">
            <p className="font-medium">This file has been re-encoded.</p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-green-600">Original Size:</span> {formatFileSize(mediaFile.size)}
              </div>
              <div>
                <span className="text-green-600">New Size:</span> {formatFileSize(mediaFile.reEncodedSize || 0)}
              </div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="cursor-help">
                      <span className="text-green-600">New Bitrate:</span> {mediaFile.reEncodedBitrate}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      Bitrate is the amount of data processed per unit of time. Higher bitrates generally 
                      mean better quality but larger file sizes.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="cursor-help">
                      <span className="text-green-600">Reduction:</span> {
                        mediaFile.reEncodedSize 
                          ? `${((1 - mediaFile.reEncodedSize / mediaFile.size) * 100).toFixed(1)}%` 
                          : 'N/A'
                      }
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      File size reduction achieved by re-encoding. A higher percentage means 
                      more space saved compared to the original file.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
          
          <Button 
            className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
            onClick={handleDownload}
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              className="h-5 w-5 mr-2" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" 
              />
            </svg>
            Download Re-encoded File
          </Button>
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-600 mb-4">
            Change the bitrate of your {activeTab === 'video' ? 'video' : 'audio'} stream. 
            Enter a value in format like {activeTab === 'video' ? '"5000k" (5 Mbps)' : '"128k" (128 kbps)'}.
          </p>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="targetBitrate"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-2">
                      <FormLabel>Target Bitrate</FormLabel>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="cursor-help rounded-full bg-slate-100 p-1 w-4 h-4 inline-flex items-center justify-center text-slate-500 text-xs">?</div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs max-w-xs">
                              {activeTab === 'video' 
                                ? 'Video bitrate affects visual quality and file size. Higher values (e.g., 5000k) give better quality but larger files.' 
                                : 'Audio bitrate affects sound quality and file size. Common values: 128k for standard quality, 320k for high quality.'}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder={activeTab === 'video' ? '5000k' : '128k'} 
                        disabled={isProcessing}
                      />
                    </FormControl>
                    <p className="text-xs text-gray-500">
                      {activeTab === 'video' 
                        ? 'For video, try 1000k-8000k (1-8 Mbps)' 
                        : 'For audio, try 96k-320k (96-320 kbps)'}
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <Button 
                type="submit" 
                className="w-full bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-600 hover:to-teal-600"
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <>
                    <span className="mr-2">Processing...</span>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  </>
                ) : (
                  <>
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      className="h-5 w-5 mr-2" 
                      fill="none" 
                      viewBox="0 0 24 24" 
                      stroke="currentColor"
                    >
                      <path 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        strokeWidth={2} 
                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" 
                      />
                    </svg>
                    Re-encode Media
                  </>
                )}
              </Button>
            </form>
          </Form>
          
          {isProcessing && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-xs text-gray-500">
                <span>Re-encoding in progress...</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
                
          {isComplete && (
            <div className="mt-4 space-y-3">
              <div className="bg-green-50 p-3 rounded-md text-sm text-green-800">
                Re-encoding complete! You can now download the re-encoded file.
              </div>
              <Button 
                className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
                onClick={handleDownload}
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className="h-5 w-5 mr-2" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" 
                  />
                </svg>
                Download Re-encoded File
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BitrateModifier;