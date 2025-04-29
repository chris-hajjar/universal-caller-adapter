/**
 * Declaration file for the fluent-ffmpeg module
 * This enables type safety when working with the module
 * 
 * Note: This application uses fluent-ffmpeg as a Node.js wrapper that calls FFmpeg as an external process.
 * FFmpeg is dynamically linked and not statically compiled into the application binary.
 * This adheres to the LGPLv2.1 licensing requirements for commercial use.
 */

declare module 'fluent-ffmpeg' {
  interface FfmpegCommand {
    // Add any method signatures used in our code
    outputOptions(options: string[]): FfmpegCommand;
    output(outputPath: string): FfmpegCommand;
    on(event: string, callback: (info?: any) => void): FfmpegCommand;
    videoBitrate(bitrate: string): FfmpegCommand;
    audioBitrate(bitrate: string): FfmpegCommand;
    run(): void;
  }

  interface ProbeData {
    format: {
      filename?: string;
      nb_streams?: number;
      format_name?: string;
      format_long_name?: string;
      start_time?: string;
      duration?: string;
      size?: string;
      bit_rate?: string;
      [key: string]: any;
    };
    streams?: Array<{
      index?: number;
      codec_name?: string;
      codec_long_name?: string;
      codec_type?: string;
      codec_tag_string?: string;
      width?: number;
      height?: number;
      r_frame_rate?: string;
      avg_frame_rate?: string;
      time_base?: string;
      bit_rate?: string;
      sample_rate?: string;
      channels?: number;
      channel_layout?: string;
      pix_fmt?: string;
      color_space?: string;
      profile?: string;
      display_aspect_ratio?: string;
      tags?: {
        language?: string;
        [key: string]: any;
      };
      [key: string]: any;
    }>;
  }

  function ffprobe(path: string, callback: (err: any, data: ProbeData) => void): void;

  namespace ffmpeg {
    export function ffprobe(path: string, callback: (err: any, data: ProbeData) => void): void;
  }

  function ffmpeg(options?: any): FfmpegCommand;
  
  export default ffmpeg;
}