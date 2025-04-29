import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import express from "express";
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
  
  // Create static directory if it doesn't exist and serve static files
  const staticDir = path.join(process.cwd(), "static");
  if (!fs.existsSync(staticDir)) {
    fs.mkdirSync(staticDir, { recursive: true });
  }
  
  // Serve static files, including FFmpeg source code
  app.use('/static', express.static(staticDir));
  
  // Specific route for FFmpeg source code download
  app.get('/ffmpeg-source.zip', (req, res) => {
    // Since we're demonstrating compliance but not actually shipping FFmpeg,
    // we'll create a simple text response with the README content
    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Content-Disposition', 'attachment; filename="ffmpeg-source.txt"');
    
    const readmePath = path.join(staticDir, 'README_FFMPEG.txt');
    const licensePath = path.join(staticDir, 'LICENSE');
    const placeholderPath = path.join(staticDir, 'ffmpeg-placeholder.txt');
    
    let contents = '';
    
    if (fs.existsSync(readmePath)) {
      contents += fs.readFileSync(readmePath, 'utf8') + '\n\n';
    }
    
    if (fs.existsSync(licensePath)) {
      contents += '==== LICENSE ====\n\n' + fs.readFileSync(licensePath, 'utf8') + '\n\n';
    }
    
    if (fs.existsSync(placeholderPath)) {
      contents += '==== SOURCE CODE PLACEHOLDER ====\n\n' + fs.readFileSync(placeholderPath, 'utf8');
    }
    
    res.send(contents);
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
