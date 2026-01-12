import { useState } from "react";

function UploadButton({ uploadedFile, setUploadedFile }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isInvalidFile, setIsInvalidFile] = useState(false);

  const isValidAudioType = (type) => {
    const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-wav'];
    return validTypes.includes(type);
  }

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();

    const items = e.dataTransfer.items;
    if (items && items.length > 0) {
      const item = items[0];

      if (item.kind === 'file') {
        const isValid = isValidAudioType(item.type);
        setIsDragging(!isValid ? false : true);
        setIsInvalidFile(!isValid);
      }
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setIsInvalidFile(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setIsInvalidFile(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];

      if (isValidAudioType(file.type)) {
        setUploadedFile(file);
      }
    }
  };

  const handleFileInput = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setUploadedFile(files[0]);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto p-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-8
          text-center
          transition-colors duration-200 ease-in-out
          ${isInvalidFile ? 'border-red-500 bg-red-50'
            : isDragging
            ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          }
        `}
      >
        <input
          type="file"
          id="fileInput"
          onChange={handleFileInput}
          className="hidden"
          accept="audio/*,.wav,.mp3"
        />
        <label
          htmlFor="fileInput"
          className="cursor-pointer"
        >
          <div className="space-y-4">
            <div className="text-6xl">
              {isInvalidFile ? '❌' : isDragging ? '📂' : '🎵'}
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-700 min-w-[20rem]">
                {isInvalidFile ? 'Format non supporté' : isDragging
                  ? 'Déposez votre fichier ici'
                  : 'Glissez-déposez votre fichier audio'
                }
              </p>
              <p className="text-sm text-gray-500 mt-2">
                ou cliquez pour parcourir
              </p>
            </div>
            <div className="text-xs text-gray-400">
              Formats acceptés: WAV, MP3
            </div>
          </div>
        </label>
      </div>

    </div>
  )
}

export default UploadButton;
