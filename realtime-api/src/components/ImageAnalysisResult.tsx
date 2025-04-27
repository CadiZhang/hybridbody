import { useEffect } from 'react';

interface ImageAnalysisResultProps {
  imageData?: string;
  analysisText?: string;
  isLoading?: boolean;
}

export function ImageAnalysisResult({ 
  imageData, 
  analysisText, 
  isLoading = false 
}: ImageAnalysisResultProps) {
  
  // Auto-scroll to the bottom when analysis text changes
  useEffect(() => {
    if (analysisText) {
      const element = document.getElementById('analysis-text');
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    }
  }, [analysisText]);
  
  return (
    <div className="bg-white/90 backdrop-blur-sm p-4 rounded-lg max-h-80 overflow-auto">
      {imageData && (
        <div className="mb-4">
          <img 
            src={imageData} 
            alt="Captured" 
            className="max-w-full max-h-40 object-contain mb-2" 
          />
          <div className="text-xs text-gray-500">Captured Image</div>
        </div>
      )}
      
      {isLoading && (
        <div className="text-sm text-gray-700">Analyzing image...</div>
      )}
      
      {analysisText && (
        <div>
          <h3 className="font-medium mb-2">Analysis:</h3>
          <p id="analysis-text" className="text-sm overflow-y-auto max-h-40">{analysisText}</p>
        </div>
      )}
      
      {!imageData && !analysisText && !isLoading && (
        <div className="text-gray-500">No image analysis available</div>
      )}
    </div>
  );
} 