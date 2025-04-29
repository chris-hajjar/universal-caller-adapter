FFmpeg Source Code and Configuration Information
===========================================================

This source code archive contains the exact version of FFmpeg used in our media processing application.

## FFmpeg Version
Version: 5.1.2
Release Date: 2022-09-25
License: LGPL 2.1+

## Compilation Configuration
Our application uses FFmpeg compiled with the following configuration:

```
./configure --prefix=/usr --disable-debug --disable-static \
  --disable-stripping --enable-shared --enable-gpl=no \
  --enable-version3=no --enable-nonfree=no \
  --enable-libfreetype --enable-libmp3lame \
  --enable-libopus --enable-libvorbis \
  --enable-libvpx --enable-opengl \
  --enable-libxvid --enable-avfilter \
  --enable-postproc --enable-pthreads \
  --enable-sdl2 \
  --disable-encoders --enable-encoder=libx264,libx265,aac,libmp3lame,libopus,libvorbis \
  --disable-muxers --enable-muxer=mp4,mp3,ogg,matroska,webm \
  --disable-protocols --enable-protocol=file,http,https,tcp,udp,rtp
```

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