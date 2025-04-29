import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { uploadMiddleware } from "./middlewares/upload";
import { 
  analyzeMedia, 
  reEncodeMedia, 
  validateBitrateFormat, 
  getEncodingProgress 
} from "./services/mediaService";
import fs from "fs";
import { promises as fsPromises } from "fs";
import path from "path";
import { MediaFileSpecs, reEncodeRequestSchema } from "@shared/schema";
import { z } from "zod";

// Constants for better organization and performance
const TEMP_DIR = path.join(process.cwd(), "tmp");
const MIME_TYPE_MAP = {
  'audio/mpeg': 'audio',
  'audio/mp3': 'audio',
  'video/mp4': 'video'
};

// Enhanced type definition for multer file
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

// Centralized error handler
const handleError = (res: Response, error: unknown, message: string, statusCode = 500): Response => {
  console.error(`${message}:`, error);
  
  // Normalize error object 
  const errorMessage = error instanceof Error ? error.message : String(error);
  
  return res.status(statusCode).json({ 
    status: 'error',
    message, 
    error: errorMessage,
    timestamp: new Date().toISOString()
  });
};

export async function registerRoutes(app: Express): Promise<Server> {
  // Ensure temp directory exists - moved from middleware to avoid duplication
  if (!fs.existsSync(TEMP_DIR)) {
    fs.mkdirSync(TEMP_DIR, { recursive: true });
  }

  // Media upload route with better error handling and performance
  app.post("/api/media/upload", uploadMiddleware.single("file"), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ status: 'error', message: "No file uploaded" });
      }

      // Get file info from multer (already validated)
      const { path: filePath, originalname, size, mimetype } = req.file;
      
      try {
        // Extract media specifications using optimized FFmpeg settings
        const mediaSpecs = await analyzeMedia(filePath);
        
        // Determine media type more efficiently by checking stream codec_type
        // Using optional chaining and fallback to MIME type for faster processing
        const mediaType = mediaSpecs.streams?.some(stream => stream.codec_type === 'video') 
          ? 'video' 
          : MIME_TYPE_MAP[mimetype as keyof typeof MIME_TYPE_MAP] || 'audio';
        
        // Save media file metadata to storage (size already provided by multer)
        const mediaFile = await storage.createMediaFile({
          filename: originalname,
          path: filePath,
          size, // Use size from multer to avoid extra fs call
          mediaType,
          specs: mediaSpecs,
          userId: null, // We're not associating with a user for now
        });

        return res.status(200).json({
          status: 'success',
          data: mediaFile
        });
      } catch (error) {
        // Clean up the temporary file if analysis fails
        await fsPromises.unlink(filePath).catch(err => {
          console.warn(`Failed to clean up file ${filePath}:`, err);
        });
        
        return handleError(res, error, "Error analyzing media file");
      }
    } catch (error) {
      return handleError(res, error, "Error uploading file");
    }
  });

  // Get a specific media file by ID with enhanced caching
  app.get("/api/media/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ status: 'error', message: "Invalid ID format" });
      }

      const mediaFile = await storage.getMediaFile(id);
      if (!mediaFile) {
        return res.status(404).json({ status: 'error', message: "Media file not found" });
      }

      // Add cache headers for better performance
      res.setHeader('Cache-Control', 'private, max-age=300'); // Cache for 5 minutes
      return res.status(200).json({
        status: 'success',
        data: mediaFile
      });
    } catch (error) {
      return handleError(res, error, "Error retrieving media file");
    }
  });
  
  // Get encoding progress for a media file
  app.get("/api/media/progress/:jobId", (req, res) => {
    try {
      const { jobId } = req.params;
      if (!jobId) {
        return res.status(400).json({ status: 'error', message: "Missing job ID" });
      }
      
      const progress = getEncodingProgress(jobId);
      
      return res.status(200).json({
        status: 'success',
        data: { progress }
      });
    } catch (error) {
      return handleError(res, error, "Error retrieving encoding progress");
    }
  });

  // Re-encode media file route with better async handling
  app.post("/api/media/reencode", async (req, res) => {
    try {
      // Validate the request body with Zod schema
      const validationResult = reEncodeRequestSchema.safeParse(req.body);
      if (!validationResult.success) {
        return res.status(400).json({ 
          status: 'error',
          message: "Invalid request data", 
          errors: validationResult.error.format() 
        });
      }
      
      const { mediaFileId, targetBitrate, streamType } = validationResult.data;
      
      // Verify media file exists
      const mediaFile = await storage.getMediaFile(mediaFileId);
      if (!mediaFile) {
        return res.status(404).json({ status: 'error', message: "Media file not found" });
      }
      
      try {
        // Get job ID for progress tracking before starting encode
        const jobId = `${path.basename(mediaFile.path)}_${Date.now()}`;
        
        // Start re-encoding asynchronously for better response time
        const reEncodePromise = reEncodeMedia(mediaFile.path, targetBitrate, streamType);
        
        // Return immediately with job ID for progress tracking
        res.status(202).json({
          status: 'processing',
          message: "Re-encoding started",
          data: { 
            mediaFileId, 
            jobId,
            progress: 0
          }
        });
        
        // Continue processing in the background
        const reEncodedResult = await reEncodePromise;
        
        // Update the media file record with re-encoded information
        await storage.updateMediaFileWithReEncoded(
          mediaFileId,
          reEncodedResult.path,
          reEncodedResult.size,
          targetBitrate
        );
        
        // Note: We don't send another response here since we already responded
      } catch (error) {
        console.error("Error in background re-encoding process:", error);
        // Cannot send error to client since response already sent
        // In a production system, we would use a notification system or 
        // allow client to poll status endpoint
      }
    } catch (error) {
      return handleError(res, error, "Error processing re-encoding request");
    }
  });
  
  // Check re-encoded media file status
  app.get("/api/media/:id/status", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ status: 'error', message: "Invalid ID" });
      }
      
      const mediaFile = await storage.getMediaFile(id);
      if (!mediaFile) {
        return res.status(404).json({ status: 'error', message: "Media file not found" });
      }
      
      // Check if re-encoding is complete
      if (mediaFile.isReEncoded && mediaFile.reEncodedPath) {
        // Verify file still exists
        const fileExists = fs.existsSync(mediaFile.reEncodedPath);
        
        return res.status(200).json({
          status: 'success',
          data: {
            isReEncoded: mediaFile.isReEncoded,
            fileExists,
            targetBitrate: mediaFile.reEncodedBitrate,
            size: mediaFile.reEncodedSize
          }
        });
      } else {
        return res.status(200).json({
          status: 'success',
          data: {
            isReEncoded: false
          }
        });
      }
    } catch (error) {
      return handleError(res, error, "Error checking re-encoded file status");
    }
  });
  
  // Download re-encoded media file route with optimized streaming
  app.get("/api/media/:id/download", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ status: 'error', message: "Invalid ID" });
      }
      
      const mediaFile = await storage.getMediaFile(id);
      if (!mediaFile) {
        return res.status(404).json({ status: 'error', message: "Media file not found" });
      }
      
      if (!mediaFile.isReEncoded || !mediaFile.reEncodedPath) {
        return res.status(400).json({ status: 'error', message: "Media file has not been re-encoded" });
      }
      
      // Check if the file exists
      if (!fs.existsSync(mediaFile.reEncodedPath)) {
        return res.status(404).json({ status: 'error', message: "Re-encoded file not found on server" });
      }
      
      // Get file stats for range requests and content-length header
      const stat = fs.statSync(mediaFile.reEncodedPath);
      const fileSize = stat.size;
      
      // Generate a cleaner filename for download
      const downloadFilename = path.basename(mediaFile.filename, path.extname(mediaFile.filename)) + 
        `_reencoded_${mediaFile.reEncodedBitrate}` + 
        path.extname(mediaFile.reEncodedPath);
      
      // Set headers for optimal download
      res.setHeader('Content-Disposition', `attachment; filename="${downloadFilename}"`);
      res.setHeader('Content-Type', 'application/octet-stream');
      res.setHeader('Content-Length', fileSize);
      res.setHeader('Accept-Ranges', 'bytes');
      
      // Support for range requests (partial content)
      const range = req.headers.range;
      if (range) {
        const parts = range.replace(/bytes=/, "").split("-");
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        
        if (start >= fileSize) {
          res.status(416).send('Requested range not satisfiable');
          return;
        }
        
        const chunkSize = (end - start) + 1;
        const fileStream = fs.createReadStream(mediaFile.reEncodedPath, { start, end });
        
        res.status(206);
        res.setHeader('Content-Range', `bytes ${start}-${end}/${fileSize}`);
        res.setHeader('Content-Length', chunkSize);
        
        fileStream.pipe(res);
      } else {
        // Send the whole file if no range is specified
        const fileStream = fs.createReadStream(mediaFile.reEncodedPath);
        fileStream.pipe(res);
      }
    } catch (error) {
      return handleError(res, error, "Error downloading re-encoded file");
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
