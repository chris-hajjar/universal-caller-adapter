import React, { FC, useState } from 'react';
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
  const { toast } = useToast();

  // Set up the form
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      targetBitrate: '',
    },
  });

  const onSubmit = async (data: FormValues) => {
    setIsProcessing(true);
    try {
      const payload = {
        mediaFileId: mediaFile.id,
        targetBitrate: data.targetBitrate,
        streamType: activeTab, // Pass the active tab to specify which stream type to modify
      };
      
      const result = await apiRequest('POST', '/api/media/reencode', payload);

      // Update cached media file data
      queryClient.invalidateQueries({ queryKey: ['/api/media', mediaFile.id] });
      
      setIsComplete(true);
      toast({
        title: 'Re-encoding Complete',
        description: 'Your media file has been successfully re-encoded.',
      });
      
    } catch (error) {
      let errorMessage = 'Failed to re-encode the media file';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast({
        title: 'Re-encoding Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async () => {
    try {
      // Create a download URL from the API endpoint
      const downloadUrl = `/api/media/${mediaFile.id}/download`;
      
      // Create a link and trigger download
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${mediaFile.filename.split('.')[0]}_reencoded${mediaFile.filename.substring(mediaFile.filename.lastIndexOf('.'))}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
    } catch (error) {
      toast({
        title: 'Download Failed',
        description: 'Failed to download the re-encoded file.',
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
              <div>
                <span className="text-green-600">New Bitrate:</span> {mediaFile.reEncodedBitrate}
              </div>
              <div>
                <span className="text-green-600">Reduction:</span> {
                  mediaFile.reEncodedSize 
                    ? `${((1 - mediaFile.reEncodedSize / mediaFile.size) * 100).toFixed(1)}%` 
                    : 'N/A'
                }
              </div>
            </div>
          </div>
          
          <Button 
            className="w-full"
            onClick={handleDownload}
          >
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
                    <FormLabel>Target Bitrate</FormLabel>
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
                className="w-full"
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <>
                    <span className="mr-2">Processing...</span>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  </>
                ) : (
                  'Re-encode Media'
                )}
              </Button>
            </form>
          </Form>
                
          {isComplete && (
            <div className="mt-4 bg-green-50 p-3 rounded-md text-sm text-green-800">
              Re-encoding complete! You can now download the re-encoded file.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BitrateModifier;