import { useState } from 'react';
import UploadButton from '../components/UploadButton';
import UploadedFile from '../components/UploadedFile';
import GenerateButton from '../components/GenerateButton';
import PdfViewer from '../components/PdfViewer';

function Home() {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response_notes = await fetch('http://localhost:8000/api/recognize-notes/', {
        method: 'POST',
        body: formData
      });
      const notes_fetched = await response_notes.json();

      const response_pdf = await fetch('http://localhost:8000/api/generate-sheet/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(notes_fetched)
      });
      const pdfBlob = await response_pdf.blob();
      const pdfUrl = URL.createObjectURL(pdfBlob);

      setPdfUrl(pdfUrl);
    } catch (error) {
      console.error('Erreur lors de la génération:', error);
      alert('Erreur lors de la génération du PDF');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className='min-h-screen py-8'>
      <div className='container mx-auto'>
        <h1 className='text-3xl font-bold text-center mb-8'>
          Upload your music file here
        </h1>

        <UploadButton
          uploadedFile={uploadedFile}
          setUploadedFile={setUploadedFile}
        />

        {uploadedFile && (
          <div className='w-full max-w-xl mx-auto space-y-4 mt-4'>
            <UploadedFile file={uploadedFile} />
            <GenerateButton
              onClick={handleGenerate}
              isGenerating={isGenerating}
            />
          </div>
        )}
        {pdfUrl && <PdfViewer url={pdfUrl} />}
      </div>
    </div>
  );
}

export default Home;
