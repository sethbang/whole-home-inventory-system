import React, { useRef, useState } from 'react';
import { XMarkIcon, CameraIcon } from '@heroicons/react/24/outline';

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export default function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      setError('Unable to access camera. Please make sure you have granted camera permissions.');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  const handleCapture = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      if (context) {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw the current video frame
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to file
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `camera-capture-${Date.now()}.jpg`, {
              type: 'image/jpeg',
            });
            onCapture(file);
            stopCamera();
            onClose();
          }
        }, 'image/jpeg');
      }
    }
  };

  React.useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full overflow-hidden">
        <div className="p-4 flex justify-between items-center border-b">
          <h3 className="text-lg font-medium">Take Photo</h3>
          <button
            onClick={() => {
              stopCamera();
              onClose();
            }}
            className="text-gray-400 hover:text-gray-500"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <div className="relative aspect-[4/3] bg-black">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center text-white text-center p-4">
              {error}
            </div>
          ) : (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="absolute inset-0 w-full h-full object-cover"
            />
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        <div className="p-4 flex justify-center">
          <button
            onClick={handleCapture}
            disabled={!!error}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CameraIcon className="h-5 w-5 mr-2" />
            Capture Photo
          </button>
        </div>
      </div>
    </div>
  );
}
