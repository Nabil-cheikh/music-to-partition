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
    formData.append('audioFile', uploadedFile);

    try {
      await new Promise(resolve => setTimeout(resolve, 3000));

      // TODO replace with :
      // const response = await fetch('http://localhost:5000/generate', {
      //   method: 'POST',
      //   body: formData
      // });
      // const { pdfUrl } = await response.json();

      setPdfUrl('/blank.pdf');
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
