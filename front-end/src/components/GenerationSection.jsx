import { useState } from 'react';
import GenerateButton from './GenerateButton';
import PdfViewer from './PdfViewer';

function GenerationSection({ file }) {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);

    const formData = new FormData();
    formData.append('file', file);

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
    <>
      <GenerateButton onClick={handleGenerate} isGenerating={isGenerating} />
      {pdfUrl && <PdfViewer url={pdfUrl} />}
    </>
  );
}

export default GenerationSection;
