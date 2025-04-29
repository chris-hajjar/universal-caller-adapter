import { FC } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const AboutDialog: FC = () => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-gray-600">
          About
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>About Media Specs Extractor</DialogTitle>
          <DialogDescription>
            Version 1.0 - Copyright © {new Date().getFullYear()}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <h4 className="font-medium text-sm">About this Application</h4>
            <p className="text-sm text-gray-600 mt-1">
              Media Specs Extractor allows you to analyze and modify media files. 
              Upload MP3 or MP4 files to extract detailed specifications, then
              optionally re-encode them with a different bitrate.
            </p>
          </div>
          
          <div>
            <h4 className="font-medium text-sm">FFmpeg Attribution</h4>
            <p className="text-sm text-gray-600 mt-1">
              This application uses libraries from the FFmpeg project under the LGPLv2.1.
              The source code can be downloaded <a href="/ffmpeg-source.zip" className="text-blue-600 hover:underline">here</a>.
            </p>
          </div>
          
          <div>
            <h4 className="font-medium text-sm">License Notice</h4>
            <div className="text-xs text-gray-500 mt-1 border-l-2 border-gray-300 pl-3 py-1">
              <p>
                This software uses code of FFmpeg licensed under the LGPLv2.1. FFmpeg is a 
                trademark of Fabrice Bellard. FFmpeg is dynamically linked in this application, 
                in accordance with the LGPL license requirements.
              </p>
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-sm">FFmpeg Configuration</h4>
            <p className="text-sm text-gray-600 mt-1">
              This application uses FFmpeg compiled without GPL and non-free components, 
              making it suitable for commercial use. The FFmpeg binary is called as 
              an external process and is not statically linked into the application.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default AboutDialog;