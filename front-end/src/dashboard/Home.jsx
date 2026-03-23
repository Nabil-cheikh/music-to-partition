import { useState } from 'react';
import UploadButton from '../components/UploadButton';
import UploadedFile from '../components/UploadedFile';
import GenerationSection from '../components/GenerationSection';

function Home() {
  const [uploadedFile, setUploadedFile] = useState(null);

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
            <GenerationSection file={uploadedFile} />
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;
