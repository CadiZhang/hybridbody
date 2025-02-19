import { useEffect, useRef } from 'react';

interface ESP32CameraProps {
  streamUrl: string;
  onError?: (error: string) => void;
}

export function ESP32Camera({ streamUrl, onError }: ESP32CameraProps) {
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    // Set up the stream
    img.src = streamUrl;
    img.onerror = () => {
      onError?.('Failed to connect to camera stream');
    };

    return () => {
      img.src = '';
    };
  }, [streamUrl, onError]);

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black">
      <img
        ref={imgRef}
        className="w-full h-full object-contain"
        alt="ESP32 Camera Stream"
      />
      <div className="absolute bottom-4 right-4 z-10">
        <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full text-sm">
          ESP32 Camera Stream
        </div>
      </div>
    </div>
  );
} 