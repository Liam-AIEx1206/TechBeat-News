/**
 * Browser capability detection for client-side video rendering.
 * Checks if WebCodecs API (VideoEncoder, AudioEncoder) is available
 * and can encode H.264 at 1080p.
 */

export function isWebCodecsSupported(): boolean {
  if (typeof window === "undefined") return false;
  return (
    typeof VideoEncoder !== "undefined" &&
    typeof VideoFrame !== "undefined" &&
    typeof AudioEncoder !== "undefined" &&
    typeof AudioDecoder !== "undefined"
  );
}

export async function checkH264Support(): Promise<boolean> {
  if (!isWebCodecsSupported()) return false;
  try {
    const result = await VideoEncoder.isConfigSupported({
      codec: "avc1.640028", // H.264 High Profile Level 4.0
      width: 1920,
      height: 1080,
      bitrate: 8_000_000,
      framerate: 30,
    });
    return result.supported === true;
  } catch {
    return false;
  }
}

export async function checkAACSupport(): Promise<boolean> {
  if (!isWebCodecsSupported()) return false;
  try {
    const result = await AudioEncoder.isConfigSupported({
      codec: "mp4a.40.2", // AAC-LC
      numberOfChannels: 1,
      sampleRate: 44100,
      bitrate: 128000,
    });
    return result.supported === true;
  } catch {
    return false;
  }
}

/**
 * Full capability check — returns true if the browser can do
 * client-side MP4 rendering with H.264 video + AAC audio.
 */
export async function canRenderClientSide(): Promise<boolean> {
  if (!isWebCodecsSupported()) return false;
  const [h264, aac] = await Promise.all([
    checkH264Support(),
    checkAACSupport(),
  ]);
  return h264 && aac;
}
