// Custom type definitions for fluent-ffmpeg
declare module 'fluent-ffmpeg' {
  namespace ffmpeg {
    interface FfmpegCommand {
      input(source: string): FfmpegCommand;
      output(destination: string): FfmpegCommand;
      outputOptions(options: string[]): FfmpegCommand;
      videoCodec(codec: string): FfmpegCommand;
      audioCodec(codec: string): FfmpegCommand;
      videoBitrate(bitrate: string): FfmpegCommand;
      audioBitrate(bitrate: string): FfmpegCommand;
      noAudio(disabled: boolean): FfmpegCommand;
      noVideo(disabled: boolean): FfmpegCommand;
      on(event: 'start', callback: (commandLine: string) => void): FfmpegCommand;
      on(event: 'progress', callback: (progress: { percent: number }) => void): FfmpegCommand;
      on(event: 'end', callback: () => void): FfmpegCommand;
      on(event: 'error', callback: (err: Error) => void): FfmpegCommand;
      run(): void;
    }

    interface FfprobeData {
      streams: Array<{
        index: number;
        codec_name: string;
        codec_long_name: string;
        codec_type: string;
        codec_tag_string: string;
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
      format: {
        filename: string;
        nb_streams: number;
        format_name: string;
        format_long_name: string;
        start_time: string;
        duration: string;
        size: string;
        bit_rate: string;
        [key: string]: any;
      };
    }

    function ffprobe(
      source: string, 
      callback: (err: Error | null, data: FfprobeData) => void
    ): void;
    
    function ffprobe(
      source: string,
      options: string[],
      callback: (err: Error | null, data: FfprobeData) => void
    ): void;
  }

  function ffmpeg(source?: string): ffmpeg.FfmpegCommand;
  export = ffmpeg;
}