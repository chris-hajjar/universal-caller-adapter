import ffmpeg from "fluent-ffmpeg";
import { promises as fs } from "fs";
import path from "path";
import { MediaFileSpecs } from "@shared/schema";

/**
 * Analyzes a media file using FFmpeg and returns detailed specifications
 * @param filePath Path to the media file
 * @returns Promise resolving to the media specifications
 */
export async function analyzeMedia(filePath: string): Promise<MediaFileSpecs> {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(filePath, (err, metadata) => {
      if (err) {
        return reject(err);
      }
      
      try {
        // Extract relevant metadata
        const specs: MediaFileSpecs = {
          format: metadata.format,
          streams: metadata.streams,
        };
        
        resolve(specs);
      } catch (error) {
        reject(error);
      }
    });
  });
}

/**
 * Clean up temporary files that are older than the specified max age
 * @param tempDir Directory containing temporary files
 * @param maxAgeMs Maximum age of files in milliseconds (default: 1 hour)
 */
export async function cleanupTempFiles(tempDir: string, maxAgeMs = 3600000): Promise<void> {
  try {
    const files = await fs.readdir(tempDir);
    const now = Date.now();
    
    for (const file of files) {
      const filePath = path.join(tempDir, file);
      const stats = await fs.stat(filePath);
      
      // If file is older than maxAgeMs, delete it
      if (now - stats.mtime.getTime() > maxAgeMs) {
        await fs.unlink(filePath);
      }
    }
  } catch (error) {
    console.error("Error cleaning up temp files:", error);
  }
}

// Start a cleanup job to run every hour
export function startCleanupJob(tempDir: string): NodeJS.Timeout {
  return setInterval(() => {
    cleanupTempFiles(tempDir).catch(err => {
      console.error("Error in cleanup job:", err);
    });
  }, 3600000); // Run every hour
}
