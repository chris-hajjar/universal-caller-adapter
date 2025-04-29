import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { uploadMiddleware } from "./middlewares/upload";
import { analyzeMedia } from "./services/mediaService";
import fs from "fs";
import path from "path";
import { MediaFileSpecs } from "@shared/schema";

export async function registerRoutes(app: Express): Promise<Server> {
  // Create temp directory for uploaded files if it doesn't exist
  const tempDir = path.join(process.cwd(), "tmp");
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

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

  const httpServer = createServer(app);

  return httpServer;
}
