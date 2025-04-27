import { useEffect, useRef } from 'react';

interface ESP32CameraProps {
  streamUrl: string;
  onCapture?: (imageData: string) => void;
  onError?: (error: string) => void;
}

export function ESP32Camera({ streamUrl, onCapture, onError }: ESP32CameraProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Function to capture the current frame
  const captureImage = () => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    
    if (!img || !canvas) return null;
    
    // Set canvas dimensions to match the image
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    
    // Draw the current frame on the canvas
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    // Call the onCapture callback with the image data
    if (onCapture) {
      onCapture(imageData);
    }
    
    return imageData;
  };

  // Make the captureImage function available externally
  useEffect(() => {
    (window as any).captureESP32Image = captureImage;
  }, []);

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
      {/* Hidden canvas for image capture */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <div className="absolute bottom-4 right-4 z-10">
        <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full text-sm">
          ESP32 Camera Stream
        </div>
      </div>
    </div>
  );
} 