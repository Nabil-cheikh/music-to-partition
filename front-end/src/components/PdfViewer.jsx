function PdfViewer({ url }) {
  return (
    <div className="w-full max-w-4xl mx-auto mt-8 p-4">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="bg-gray-800 text-white px-6 py-4">
          <h2 className="text-xl font-semibold">Generated Sheet Music</h2>
        </div>
        <iframe
          src={url}
          className="w-full h-[800px]"
          title="Generated Sheet Music"
        />
      </div>
    </div>
  );
}

export default PdfViewer;
