import React, { useState } from 'react';
import { ChevronLeftIcon, ChevronRightIcon, XMarkIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import JSZip from 'jszip';

interface Image {
  id: string;
  filename: string;
}

interface ImageGalleryProps {
  images: Image[];
  onDelete?: (imageId: string) => void;
}

export default function ImageGallery({ images, onDelete }: ImageGalleryProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());

  const nextImage = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % images.length);
  };

  const previousImage = () => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + images.length) % images.length);
  };

  const handleImageClick = () => {
    setShowModal(true);
  };

  const handleDownload = async (imageId: string) => {
    try {
      const response = await fetch(`/uploads/${images[currentIndex].filename}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = images[currentIndex].filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download image:', error);
    }
  };

  const handleBulkDownload = async () => {
    try {
      const zip = new JSZip();
      const selectedImagesArray = Array.from(selectedImages);
      
      // Create a folder in the zip for the images
      const imgFolder = zip.folder("images");
      
      // Add each selected image to the zip
      const downloadPromises = selectedImagesArray.map(async (imageId) => {
        const image = images.find(img => img.id === imageId);
        if (image) {
          const response = await fetch(`/uploads/${image.filename}`);
          const blob = await response.blob();
          imgFolder?.file(image.filename, blob);
        }
      });
      
      // Wait for all images to be added to the zip
      await Promise.all(downloadPromises);
      
      // Generate the zip file
      const content = await zip.generateAsync({
        type: "blob",
        compression: "DEFLATE",
        compressionOptions: {
          level: 6
        }
      });
      
      // Download the zip file
      const url = window.URL.createObjectURL(content);
      const a = document.createElement('a');
      a.href = url;
      a.download = `images-${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Clear selection after download
      setSelectedImages(new Set());
    } catch (error) {
      console.error('Failed to download images:', error);
    }
  };

  const toggleImageSelection = (imageId: string) => {
    const newSelection = new Set(selectedImages);
    if (newSelection.has(imageId)) {
      newSelection.delete(imageId);
    } else {
      newSelection.add(imageId);
    }
    setSelectedImages(newSelection);
  };

  if (!images.length) return null;

  return (
    <div className="space-y-4">
      {/* Carousel */}
      <div className="relative max-w-4xl mx-auto">
        <div className="aspect-w-16 aspect-h-9 overflow-hidden rounded-lg bg-gray-200">
          <div className="flex items-center justify-center w-full h-full">
            <img
              src={`/uploads/${images[currentIndex].filename}`}
              alt=""
              className="object-contain max-h-[400px] w-auto cursor-pointer hover:opacity-95 transition-opacity"
              onClick={handleImageClick}
            />
          </div>
          {images.length > 1 && (
            <>
              <button
                type="button"
                onClick={previousImage}
                className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 rounded-full p-2 text-white hover:bg-black/75"
              >
                <ChevronLeftIcon className="h-6 w-6" />
              </button>
              <button
                type="button"
                onClick={nextImage}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 rounded-full p-2 text-white hover:bg-black/75"
              >
                <ChevronRightIcon className="h-6 w-6" />
              </button>
            </>
          )}
        </div>
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex space-x-2">
          {images.map((_, index) => (
            <button
              type="button"
              key={index}
              className={`h-2 w-2 rounded-full ${
                index === currentIndex ? 'bg-white' : 'bg-white/50'
              }`}
              onClick={() => setCurrentIndex(index)}
            />
          ))}
        </div>
      </div>

      {/* Thumbnails */}
      <div className="grid grid-cols-4 gap-2 mt-2">
        {images.map((image, index) => (
          <div key={image.id} className="relative group">
            <div className={`
              aspect-w-1 aspect-h-1 overflow-hidden rounded-lg bg-gray-200
              ${currentIndex === index ? 'ring-2 ring-primary-500' : ''}
              ${selectedImages.has(image.id) ? 'ring-2 ring-blue-500' : ''}
            `}>
              <img
                src={`/uploads/${image.filename}`}
                alt=""
                className="object-cover cursor-pointer"
                onClick={() => setCurrentIndex(index)}
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity">
                <input
                  type="checkbox"
                  className="absolute top-2 left-2"
                  checked={selectedImages.has(image.id)}
                  onChange={() => toggleImageSelection(image.id)}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex justify-between items-center mt-4">
        <div className="flex space-x-2">
          {selectedImages.size > 0 && (
            <button
              type="button"
              onClick={handleBulkDownload}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
              Download Selected ({selectedImages.size})
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => handleDownload(images[currentIndex].id)}
          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        >
          <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
          Download Current
        </button>
      </div>

      {/* Full-size image modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-75 flex items-center justify-center">
          <div className="relative max-w-7xl mx-auto p-4">
            <button
              type="button"
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 text-white hover:text-gray-300"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
            <div className="flex items-center justify-center w-full h-full">
              <img
                src={`/uploads/${images[currentIndex].filename}`}
                alt=""
                className="max-h-[90vh] max-w-[90vw] w-auto mx-auto object-contain hover:opacity-95 transition-opacity"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}