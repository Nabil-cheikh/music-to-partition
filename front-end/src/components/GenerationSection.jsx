import { useState } from 'react';
import GenerateButton from './GenerateButton';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function errorMessage(response, step) {
  const body = await response.json().catch(() => null);
  return `${step} (${response.status})${body?.detail ? ` : ${body.detail}` : ''}`;
}

function GenerationSection({ file, onPdfGenerated }) {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response_notes = await fetch(`${API_URL}/api/recognize-notes/`, {
        method: 'POST',
        body: formData
      });
      if (!response_notes.ok) {
        throw new Error(await errorMessage(response_notes, 'Reconnaissance des notes échouée'));
      }
      const notes_fetched = await response_notes.json();

      const response_pdf = await fetch(`${API_URL}/api/generate-sheet/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(notes_fetched)
      });
      if (!response_pdf.ok) {
        throw new Error(await errorMessage(response_pdf, 'Génération du PDF échouée'));
      }
      const pdfBlob = await response_pdf.blob();
      const pdfUrl = URL.createObjectURL(pdfBlob);

      onPdfGenerated(pdfUrl);
    } catch (error) {
      console.error('Erreur lors de la génération:', error);
      alert(error.message || 'Erreur lors de la génération du PDF');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <GenerateButton onClick={handleGenerate} isGenerating={isGenerating} />
  );
}

export default GenerationSection;
