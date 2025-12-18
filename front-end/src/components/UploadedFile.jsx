function UploadedFile({ file }) {
  return (
    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
      <p className="text-sm font-medium text-green-800">
        ✓ Fichier sélectionné
      </p>
      <p className="text-sm text-green-600 mt-1">
        {file.name} - ({(file.size / 1024 / 1024).toFixed(2)} MB)
      </p>
    </div>
  )
}

export default UploadedFile;
