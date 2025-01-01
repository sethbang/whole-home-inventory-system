import React from 'react';
import { ItemImage } from '../api/client';

export interface ImageGalleryProps {
  images: ItemImage[];
  onDelete?: (imageId: string) => void;
}

export default function ImageGallery({ images, onDelete }: ImageGalleryProps) {
  const handleDelete = async (imageId: string) => {
    if (onDelete) {
      onDelete(imageId);
    }
  };

  const handleDownload = async (imageId: string) => {
    // Download functionality will be implemented later
    console.log('Download image:', imageId);
  };

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {images.map((image) => (
        <div key={image.id} className="relative group">
          <img
            src={image.file_path}
            alt={image.filename}
            className="h-40 w-full object-cover rounded-lg"
          />
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-opacity rounded-lg flex items-center justify-center">
            <div className="hidden group-hover:flex space-x-2">
              {onDelete && (
                <button
                  onClick={() => handleDelete(image.id)}
                  className="p-2 bg-red-600 text-white rounded-full hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}