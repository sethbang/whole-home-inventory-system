import { useRef, useState, useCallback, useEffect } from 'react';
import { XMarkIcon, CameraIcon, QrCodeIcon } from '@heroicons/react/24/outline';
import { BrowserMultiFormatReader, Result } from '@zxing/library';

interface BarcodeScannerProps {
  onCapture: (file: File) => void;
  onBarcodeScan: (result: string) => void;
  onClose: () => void;
}

export default function BarcodeScanner({ onCapture, onBarcodeScan, onClose }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(true);
  const [lastScanned, setLastScanned] = useState<string | null>(null);
  const readerRef = useRef<BrowserMultiFormatReader | null>(null);
  // Keep the stream in a ref so stopCamera has stable identity and the
  // unmount cleanup isn't recreated every time `stream` state changes.
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      streamRef.current = mediaStream;
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch {
      setError(
        'Unable to access camera. Please make sure you have granted camera permissions.',
      );
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setStream(null);
    }
    if (readerRef.current) {
      readerRef.current.reset();
    }
  }, []);

  const handleCapture = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      if (context) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

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

  const initBarcodeReader = useCallback(async () => {
    if (!readerRef.current && videoRef.current) {
      const reader = new BrowserMultiFormatReader();
      readerRef.current = reader;
      
      try {
        await reader.decodeFromVideoDevice(
          null,
          videoRef.current,
          (result: Result | null) => {
            if (result && result.getText() !== lastScanned) {
              setLastScanned(result.getText());
              onBarcodeScan(result.getText());
              // Briefly pause scanning after successful scan
              setIsScanning(false);
              setTimeout(() => setIsScanning(true), 2000);
            }
          }
        );
      } catch (err) {
        console.error('Error initializing barcode reader:', err);
        setError('Failed to initialize barcode scanner.');
      }
    }
  }, [lastScanned, onBarcodeScan]);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, [startCamera, stopCamera]);

  useEffect(() => {
    if (stream && videoRef.current && isScanning) {
      initBarcodeReader();
    }
    return () => {
      if (readerRef.current) {
        readerRef.current.reset();
      }
    };
  }, [stream, isScanning, initBarcodeReader]);

  return (
    <div className="fixed inset-0 bg-overlay bg-opacity-75 z-50 flex items-center justify-center p-4">
      <div className="bg-surface-raised rounded-lg shadow-xl max-w-lg w-full overflow-hidden">
        <div className="p-4 flex justify-between items-center border-b">
          <h3 className="text-lg font-medium">Scan Barcode or Take Photo</h3>
          <button
            onClick={() => {
              stopCamera();
              onClose();
            }}
            className="text-subtle hover:text-subtle"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <div className="relative aspect-[4/3] bg-overlay">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center text-white text-center p-4">
              {error}
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-64 h-64 border-2 border-white/50 rounded-lg"></div>
              </div>
              {!isScanning && lastScanned && (
                <div className="absolute bottom-4 left-0 right-0 mx-auto text-center">
                  <div className="bg-success text-white px-4 py-2 rounded-full inline-flex items-center">
                    <QrCodeIcon className="h-5 w-5 mr-2" />
                    Code Scanned!
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        <div className="p-4 flex justify-center space-x-4">
          <button
            onClick={handleCapture}
            disabled={!!error}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CameraIcon className="h-5 w-5 mr-2" />
            Take Photo
          </button>
        </div>
      </div>
    </div>
  );
}