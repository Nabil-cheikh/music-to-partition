function GenerateButton({ onClick, isGenerating }) {
  return (
    <button
      onClick={onClick}
      disabled={isGenerating}
      className={`
        w-full py-4 px-6
        text-white font-semibold text-lg
        rounded-xl
        transition-all duration-200
        shadow-lg
        flex items-center justify-center gap-3
        ${isGenerating
          ? 'bg-gray-400 cursor-not-allowed'
          : 'bg-green-700 hover:bg-green-600 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0'
        }
      `}
    >
      {isGenerating ? (
        <>
          <span className="animate-spin">⏳</span>
          Generating...
        </>
      ) : (
        <>
          Generate sheet
        </>
      )}
    </button>
  );
}

export default GenerateButton;
