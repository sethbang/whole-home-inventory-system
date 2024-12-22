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

  const isIOSPWA = () => {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                        (window.navigator as any).standalone ||
                        document.referrer.includes('ios-app://');
    return isIOS && isStandalone;
  };

  const startCamera = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Camera access is not supported in this browser.');
      return;
    }

    try {
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const isChrome = /CriOS/.test(navigator.userAgent);
      const isPWA = isIOSPWA();

      // For iOS PWA, we need to ensure we're using the right constraints
      const constraints = {
        video: {
          facingMode: 'environment',
          width: isIOS ? { ideal: 1920, max: 1920 } : undefined,
          height: isIOS ? { ideal: 1080, max: 1080 } : undefined,
        }
      };

      // Try to get camera access
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
      // Wait for video element to be ready
      const waitForVideo = async () => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          // Ensure video plays on iOS
          try {
            await videoRef.current.play();
          } catch (playError) {
            console.error('Error playing video:', playError);
            // If play fails, try again after a short delay
            setTimeout(waitForVideo, 100);
          }
        } else {
          // If video element isn't ready, try again after a short delay
          setTimeout(waitForVideo, 100);
        }
      };
      await waitForVideo();
    } catch (err) {
      const error = err as Error;
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const isChrome = /CriOS/.test(navigator.userAgent);
      const isPWA = isIOSPWA();
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        if (isIOS) {
          if (isPWA) {
            setError(
              'Camera access was denied. Please close this app completely, go to iOS Settings > WHIS > Camera, enable access, then reopen the app.'
            );
          } else if (isChrome) {
            setError(
              'Camera access was denied. To enable: Go to iOS Settings > Chrome > Camera, then allow access for this site.'
            );
          } else {
            setError(
              'Camera access was denied. For local development, make sure to use https:// or enable camera access in iOS Settings > Safari > Camera, then allow access for this site.'
            );
          }
        } else {
          setError(
            'Camera access was denied. Please allow camera access when prompted.'
          );
        }
      } else {
        setError('Unable to access camera. Please make sure your device has a working camera.');
      }
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

  const requestCameraPermission = async () => {
    // For iOS PWA, we need to request permissions differently
    if (isIOSPWA()) {
      try {
        // Try to get a temporary stream just to trigger the permission prompt
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tempStream.getTracks().forEach(track => track.stop());
        // If we get here, permission was granted, so start the real camera
        await startCamera();
      } catch (err) {
        // If permission was denied, show PWA-specific instructions
        const error = err as Error;
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          setError(
            'Camera access was denied. Please close this app completely, go to iOS Settings > WHIS > Camera, enable access, then reopen the app.'
          );
        } else {
          await startCamera(); // Try regular camera start for other errors
        }
      }
    } else {
      // For non-PWA, start camera normally
      await startCamera();
    }
  };

  React.useEffect(() => {
    requestCameraPermission();
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
              <div className="max-w-sm">
                <p className="mb-4">{error}</p>
                {error.includes('Camera access was denied') && (
                  <div className="text-sm opacity-80">
                    <p className="mb-2">Steps to enable:</p>
                    {error.includes('WHIS > Camera') ? (
                      <ol className="list-decimal list-inside text-left">
                        <li>Close this app completely (swipe up to remove)</li>
                        <li>Open iOS Settings</li>
                        <li>Scroll down to WHIS</li>
                        <li>Tap Camera</li>
                        <li>Enable camera access</li>
                        <li>Reopen the app</li>
                      </ol>
                    ) : error.includes('Chrome') ? (
                      <ol className="list-decimal list-inside text-left">
                        <li>Open iOS Settings</li>
                        <li>Scroll down to Chrome</li>
                        <li>Tap Camera</li>
                        <li>Find this website and select "Allow"</li>
                        <li>Return here and refresh the page</li>
                      </ol>
                    ) : error.includes('Safari') ? (
                      <ol className="list-decimal list-inside text-left">
                        <li>Open iOS Settings</li>
                        <li>Scroll down to Safari</li>
                        <li>Tap Camera</li>
                        <li>Find this website and select "Allow"</li>
                        <li>Return here and refresh the page</li>
                      </ol>
                    ) : (
                      <p>When prompted, click "Allow" to give this site access to your camera.</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted // Required for iOS autoplay
              controls={false}
              className="absolute inset-0 w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }} // Mirror the camera view
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
