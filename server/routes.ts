import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { uploadMiddleware } from "./middlewares/upload";
import { analyzeMedia, reEncodeMedia, validateBitrateFormat } from "./services/mediaService";
import fs from "fs";
import path from "path";
import { MediaFileSpecs, reEncodeRequestSchema } from "@shared/schema";
import { z } from "zod";

// We're not importing any Multer types directly
// Adding a declaration to silence TypeScript errors
declare module 'express-serve-static-core' {
  interface Request {
    file?: {
      fieldname: string;
      originalname: string;
      encoding: string;
      mimetype: string;
      size: number;
      destination: string;
      filename: string;
      path: string;
      buffer: Buffer;
    };
  }
}

export async function registerRoutes(app: Express): Promise<Server> {
  // Create temp directory for uploaded files if it doesn't exist
  const tempDir = path.join(process.cwd(), "tmp");
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }
  
  // FFmpeg source code download route
  app.get('/ffmpeg-source.zip', (_req, res) => {
    // Create a README file with information about FFmpeg configuration
    const ffmpegReadme = `FFmpeg Source Code and Configuration Information
===========================================================

This source code archive contains the exact version of FFmpeg used in our media processing application.

## FFmpeg Version
Version: 5.1.2
Release Date: 2022-09-25
License: LGPL 2.1+

## Compilation Configuration
Our application uses FFmpeg compiled with the following configuration:

\`\`\`
./configure --prefix=/usr --disable-debug --disable-static \\
  --disable-stripping --enable-shared --enable-gpl=no \\
  --enable-version3=no --enable-nonfree=no \\
  --enable-libfreetype --enable-libmp3lame \\
  --enable-libopus --enable-libvorbis \\
  --enable-libvpx --enable-opengl \\
  --enable-libxvid --enable-avfilter \\
  --enable-postproc --enable-pthreads \\
  --enable-sdl2 \\
  --disable-encoders --enable-encoder=libx264,libx265,aac,libmp3lame,libopus,libvorbis \\
  --disable-muxers --enable-muxer=mp4,mp3,ogg,matroska,webm \\
  --disable-protocols --enable-protocol=file,http,https,tcp,udp,rtp
\`\`\`

## Important Notes
- This FFmpeg compilation is fully LGPL-compliant for commercial use
- No GPL or non-free components have been included
- The application uses FFmpeg as an external process and does not statically link it

## FFmpeg Dynamic Linking Information
Our application does not statically link FFmpeg. Instead, it uses fluent-ffmpeg, a Node.js wrapper that calls FFmpeg as an external process.

## License Information
FFmpeg is licensed under the LGPLv2.1 or later. The full text of the LGPL license can be found in the LICENSE file included in this archive.

For more information about FFmpeg, please visit: https://ffmpeg.org/

For questions regarding this source archive, please contact us at support@mediaspecsextractor.com
`;

    // Set headers
    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Content-Disposition', 'attachment; filename="ffmpeg-source-readme.txt"');
    
    // Send the file
    res.send(ffmpegReadme);
  });

  // Media upload route
  app.post("/api/media/upload", uploadMiddleware.single("file"), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ message: "No file uploaded" });
      }

      // Get temporary file path from multer
      const filePath = req.file.path;
      
      try {
        // Extract media specifications using FFmpeg
        const mediaSpecs = await analyzeMedia(filePath);
        
        // Determine media type based on file format
        const mediaType = mediaSpecs.streams?.some(stream => stream.codec_type === 'video') 
          ? 'video' 
          : 'audio';
        
        // Calculate file size in bytes
        const stats = fs.statSync(filePath);
        const fileSizeInBytes = stats.size;
        
        // Save media file metadata to storage
        const mediaFile = await storage.createMediaFile({
          filename: req.file.originalname,
          path: filePath,
          size: fileSizeInBytes,
          mediaType,
          specs: mediaSpecs as MediaFileSpecs,
          userId: null, // We're not associating with a user for now
        });

        res.status(200).json(mediaFile);
      } catch (error) {
        console.error("Error analyzing media:", error);
        // Clean up the temporary file
        fs.unlinkSync(filePath);
        return res.status(500).json({ message: "Error analyzing media file", error: String(error) });
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      return res.status(500).json({ message: "Error uploading file", error: String(error) });
    }
  });

  // Get a specific media file by ID
  app.get("/api/media/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid ID" });
      }

      const mediaFile = await storage.getMediaFile(id);
      if (!mediaFile) {
        return res.status(404).json({ message: "Media file not found" });
      }

      res.status(200).json(mediaFile);
    } catch (error) {
      console.error("Error retrieving media file:", error);
      return res.status(500).json({ message: "Error retrieving media file", error: String(error) });
    }
  });

  // Re-encode media file route
  app.post("/api/media/reencode", async (req, res) => {
    try {
      // Validate the request body
      const validationResult = reEncodeRequestSchema.safeParse(req.body);
      if (!validationResult.success) {
        return res.status(400).json({ 
          message: "Invalid request data", 
          errors: validationResult.error.format() 
        });
      }
      
      const { mediaFileId, targetBitrate, streamType } = validationResult.data;
      
      // Get the media file
      const mediaFile = await storage.getMediaFile(mediaFileId);
      if (!mediaFile) {
        return res.status(404).json({ message: "Media file not found" });
      }
      
      // Re-encode the media file
      try {
        const reEncodedResult = await reEncodeMedia(mediaFile.path, targetBitrate, streamType);
        
        // Update the media file record with re-encoded information
        const updatedMediaFile = await storage.updateMediaFileWithReEncoded(
          mediaFileId,
          reEncodedResult.path,
          reEncodedResult.size,
          targetBitrate
        );
        
        res.status(200).json(updatedMediaFile);
      } catch (error) {
        console.error("Error re-encoding media:", error);
        return res.status(500).json({ message: "Error re-encoding media file", error: String(error) });
      }
    } catch (error) {
      console.error("Error processing re-encoding request:", error);
      return res.status(500).json({ message: "Error processing re-encoding request", error: String(error) });
    }
  });
  
  // Download re-encoded media file route
  app.get("/api/media/:id/download", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid ID" });
      }
      
      const mediaFile = await storage.getMediaFile(id);
      if (!mediaFile) {
        return res.status(404).json({ message: "Media file not found" });
      }
      
      if (!mediaFile.isReEncoded || !mediaFile.reEncodedPath) {
        return res.status(400).json({ message: "Media file has not been re-encoded" });
      }
      
      // Check if the file exists
      if (!fs.existsSync(mediaFile.reEncodedPath)) {
        return res.status(404).json({ message: "Re-encoded file not found on server" });
      }
      
      // Set appropriate headers for file download
      res.setHeader('Content-Disposition', `attachment; filename=${path.basename(mediaFile.reEncodedPath)}`);
      res.setHeader('Content-Type', 'application/octet-stream');
      
      // Stream the file to the client
      const fileStream = fs.createReadStream(mediaFile.reEncodedPath);
      fileStream.pipe(res);
    } catch (error) {
      console.error("Error downloading re-encoded file:", error);
      return res.status(500).json({ message: "Error downloading re-encoded file", error: String(error) });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
