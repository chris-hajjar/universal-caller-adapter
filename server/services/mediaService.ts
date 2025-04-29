import ffmpeg from "fluent-ffmpeg";
import { promises as fs } from "fs";
import { existsSync } from "fs";
import path from "path";
import { MediaFileSpecs, BitrateFormat } from "@shared/schema";
import { promisify } from "util";
import { cpus } from "os";

// Define constants to avoid string literals
const TEMP_DIR = path.join(process.cwd(), "tmp");
const HOUR_IN_MS = 3600000;

// Define FFmpeg presets for faster encoding
const FAST_ENCODING_PRESET = "veryfast";
const THREADS = Math.max(2, Math.min(cpus().length - 1, 8)); // Use available CPU cores (min 2, max 8)

/**
 * Creates a type-safe wrapper for FFmpeg metadata
 */
interface FFprobeMetadata {
  format: Record<string, any>;
  streams: Array<Record<string, any>>;
}

/**
 * More efficient media analysis using FFmpeg with optimized settings
 * @param filePath Path to the media file
 * @returns Promise resolving to the media specifications
 */
export async function analyzeMedia(filePath: string): Promise<MediaFileSpecs> {
  // Validate file existence first to fail fast
  if (!existsSync(filePath)) {
    throw new Error(`Input file not found: ${filePath}`);
  }

  return new Promise((resolve, reject) => {
    // Set specific options to speed up probe
    const ffprobeOptions = [
      '-v', 'error',   // Less verbose output
      '-threads', String(THREADS), // Use multiple threads
      '-show_format',  // Show format info
      '-show_streams', // Show stream info
      '-print_format', 'json', // Output in JSON format
    ];
    
    ffmpeg.ffprobe(filePath, ffprobeOptions, (err, metadata: FFprobeMetadata) => {
      if (err) {
        return reject(err);
      }
      
      try {
        // Extract and filter only necessary metadata to reduce memory usage
        const specs: MediaFileSpecs = {
          format: {
            filename: metadata.format.filename,
            nb_streams: metadata.format.nb_streams,
            format_name: metadata.format.format_name,
            format_long_name: metadata.format.format_long_name,
            start_time: metadata.format.start_time,
            duration: metadata.format.duration,
            size: metadata.format.size,
            bit_rate: metadata.format.bit_rate,
          },
          streams: metadata.streams.map(stream => ({
            index: stream.index,
            codec_name: stream.codec_name,
            codec_long_name: stream.codec_long_name,
            codec_type: stream.codec_type,
            codec_tag_string: stream.codec_tag_string,
            width: stream.width,
            height: stream.height,
            r_frame_rate: stream.r_frame_rate,
            avg_frame_rate: stream.avg_frame_rate,
            time_base: stream.time_base,
            bit_rate: stream.bit_rate,
            sample_rate: stream.sample_rate,
            channels: stream.channels,
            channel_layout: stream.channel_layout,
            pix_fmt: stream.pix_fmt,
            color_space: stream.color_space,
            profile: stream.profile,
            display_aspect_ratio: stream.display_aspect_ratio,
            tags: stream.tags,
          })),
        };
        
        resolve(specs);
      } catch (error) {
        reject(error);
      }
    });
  });
}

/**
 * Optimized function to clean up temporary files
 * @param tempDir Directory containing temporary files
 * @param maxAgeMs Maximum age of files in milliseconds
 */
export async function cleanupTempFiles(tempDir: string = TEMP_DIR, maxAgeMs = HOUR_IN_MS): Promise<void> {
  try {
    // Read all files at once
    const files = await fs.readdir(tempDir);
    const now = Date.now();
    
    // Process files in parallel with a reasonable concurrency limit
    const deletePromises = files.map(async (file) => {
      try {
        const filePath = path.join(tempDir, file);
        const stats = await fs.stat(filePath);
        
        // Delete files that are older than maxAgeMs
        if (now - stats.mtime.getTime() > maxAgeMs) {
          return fs.unlink(filePath);
        }
      } catch (err) {
        // Silently ignore individual file errors
        console.warn(`Failed to process ${file} during cleanup:`, err);
      }
    });
    
    // Wait for all delete operations to complete
    await Promise.allSettled(deletePromises);
  } catch (error) {
    console.error("Error cleaning up temp files:", error);
  }
}

/**
 * Start a cleanup job with better error handling
 */
export function startCleanupJob(tempDir: string = TEMP_DIR): NodeJS.Timeout {
  console.log(`Starting cleanup job for ${tempDir}`);
  
  // Run once immediately to clean up old files
  cleanupTempFiles(tempDir).catch(err => {
    console.error("Initial cleanup error:", err);
  });
  
  // Return interval for regular cleanup
  return setInterval(() => {
    cleanupTempFiles(tempDir).catch(err => {
      console.error("Error in cleanup job:", err);
    });
  }, HOUR_IN_MS); 
}

// Progress monitoring cache for status updates
const encodingProgress = new Map<string, number>();

/**
 * Optimized media re-encoding with progress tracking and better performance
 * @param inputPath Path to the input media file
 * @param targetBitrate Target bitrate
 * @param streamType Stream type to re-encode
 * @returns Promise resolving to file info
 */
export async function reEncodeMedia(
  inputPath: string, 
  targetBitrate: BitrateFormat,
  streamType: 'video' | 'audio' = 'video'
): Promise<{ path: string; size: number }> {
  // Validate file existence synchronously to fail fast
  if (!existsSync(inputPath)) {
    throw new Error(`Input file not found: ${inputPath}`);
  }
  
  // Create unique identifier for tracking progress
  const jobId = `${path.basename(inputPath)}_${Date.now()}`;
  encodingProgress.set(jobId, 0);
  
  // Generate output path with better organization
  const fileExt = path.extname(inputPath);
  const fileName = path.basename(inputPath, fileExt);
  const outputPath = path.join(
    path.dirname(inputPath),
    `${fileName}_reencoded_${streamType}_${targetBitrate}${fileExt}`
  );
  
  return new Promise((resolve, reject) => {
    try {
      // Setup FFmpeg command with optimized settings
      let command = ffmpeg(inputPath)
        .output(outputPath)
        .outputOptions(['-threads', String(THREADS)]) // Use multiple threads
        .noAudio(false)
        .noVideo(false);
      
      // Codec selection optimization
      if (streamType === 'video') {
        command = command
          .videoCodec('libx264')           // More efficient codec
          .outputOptions([
            `-preset ${FAST_ENCODING_PRESET}`, // Fast encoding
            '-movflags +faststart',        // Optimize for streaming
            '-tune film'                   // Optimize for general content
          ])
          .videoBitrate(targetBitrate)     // Set video bitrate
          .audioBitrate('128k');           // Keep audio quality reasonable
      } else {
        command = command
          .audioCodec('aac')              // More efficient audio codec
          .audioBitrate(targetBitrate)    // Set audio bitrate
          .outputOptions([
            '-strict experimental',       // Allow experimental codecs
            '-ar 44100'                   // Standard audio sample rate
          ]);
        
        // Copy video stream if present (don't re-encode)
        if (fileExt.toLowerCase() === '.mp4') {
          command = command.videoCodec('copy');
        }
      }
      
      // Add progress tracking
      command.on('progress', (progress) => {
        encodingProgress.set(jobId, Math.round(progress.percent || 0));
      });
      
      command.on('end', async () => {
        try {
          // Get file size and clean up progress tracking
          const stats = await fs.stat(outputPath);
          encodingProgress.delete(jobId);
          
          resolve({
            path: outputPath,
            size: stats.size
          });
        } catch (error) {
          reject(error);
        }
      });
      
      command.on('error', (err) => {
        // Clean up tracking on error
        encodingProgress.delete(jobId);
        reject(err);
      });
      
      // Start encoding process
      command.run();
    } catch (error) {
      // Ensure we clean up tracking even on unexpected errors
      encodingProgress.delete(jobId);
      reject(error);
    }
  });
}

/**
 * Get current progress of any ongoing encoding job
 * @param jobId The job identifier
 * @returns Progress percentage (0-100)
 */
export function getEncodingProgress(jobId: string): number {
  return encodingProgress.get(jobId) || 0;
}

/**
 * Validates a bitrate string format with stronger validation
 * @param bitrate Bitrate string
 * @returns Boolean indicating if format is valid
 */
export function validateBitrateFormat(bitrate: string): boolean {
  // More precise regex for bitrate format validation
  const bitrateRegex = /^(?:[1-9]\d{0,6}|0)(?:k|M)?$/;
  
  // Additional validation for reasonable values
  if (!bitrateRegex.test(bitrate)) {
    return false;
  }
  
  // Check for reasonable limits
  const numericValue = parseInt(bitrate.replace(/[kM]$/, ''));
  
  if (bitrate.endsWith('M')) {
    // For Mbps, reasonable range is 1-50
    return numericValue >= 1 && numericValue <= 50;
  } else if (bitrate.endsWith('k')) {
    // For kbps, reasonable range is 8-8000
    return numericValue >= 8 && numericValue <= 8000;
  }
  
  // Raw numbers (assumed bits/sec) should be reasonable
  return numericValue >= 8000 && numericValue <= 50000000;
}
