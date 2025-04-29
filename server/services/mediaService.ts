import ffmpeg from "fluent-ffmpeg";
import { promises as fs } from "fs";
import * as fsSync from "fs";
import path from "path";
import { MediaFileSpecs, BitrateFormat } from "@shared/schema";

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

/**
 * Re-encodes a media file with a new bitrate
 * @param inputPath Path to the input media file
 * @param targetBitrate Target bitrate in format like '5000k' or '5M'
 * @returns Promise resolving to the path of the re-encoded file
 */
export async function reEncodeMedia(
  inputPath: string, 
  targetBitrate: BitrateFormat,
  streamType: 'video' | 'audio' = 'video'
): Promise<{ path: string; size: number }> {
  return new Promise((resolve, reject) => {
    try {
      // Get file extension from original file
      const fileExt = path.extname(inputPath);
      const fileName = path.basename(inputPath, fileExt);
      
      // Create output path in same directory as input
      const outputPath = path.join(
        path.dirname(inputPath),
        `${fileName}_reencoded_${streamType}_${targetBitrate}${fileExt}`
      );
      
      // Check if the file exists first
      if (!fsSync.existsSync(inputPath)) {
        return reject(new Error(`Input file not found: ${inputPath}`));
      }
      
      // Start re-encoding process
      let command = ffmpeg(inputPath)
        .output(outputPath)
        .outputOptions('-y') // Overwrite output files without asking
        .on('start', (commandLine) => {
          console.log('FFmpeg process started with command:', commandLine);
        })
        .on('progress', (progress) => {
          console.log('Re-encoding progress:', progress);
        });
      
      // Set bitrate based on stream type
      if (streamType === 'video') {
        command = command
          .videoBitrate(targetBitrate)   // Set video bitrate
          .audioBitrate('128k');         // Keep audio at reasonable quality
      } else {
        command = command
          .audioBitrate(targetBitrate);  // Set audio bitrate
          // Keep video settings unchanged
      }
      
      command
        .on('end', async () => {
          try {
            console.log('FFmpeg process completed successfully');
            // Get file size of the re-encoded file
            const stats = await fs.stat(outputPath);
            
            resolve({
              path: outputPath,
              size: stats.size
            });
          } catch (error) {
            console.error('Error getting re-encoded file stats:', error);
            reject(error);
          }
        })
        .on('error', (err) => {
          console.error('FFmpeg process error:', err);
          reject(err);
        });
      
      try {
        // Start the encoding process
        command.run();
      } catch (execError) {
        console.error('Error executing FFmpeg command:', execError);
        reject(execError);
      }
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Validates a bitrate string format
 * @param bitrate Bitrate string (e.g., "5000k", "5M")
 * @returns Boolean indicating if the format is valid
 */
export function validateBitrateFormat(bitrate: string): boolean {
  const bitrateRegex = /^\d+(k|M)?$/;
  return bitrateRegex.test(bitrate);
}
