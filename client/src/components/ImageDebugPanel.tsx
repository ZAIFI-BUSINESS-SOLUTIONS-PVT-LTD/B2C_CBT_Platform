import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import normalizeImageSrc from "@/lib/media";

/**
 * Debug component to test base64 image rendering
 * Add this temporarily to your test interface to diagnose issues
 */
export function ImageDebugPanel({ question }: { question: any }) {
  const [showDebug, setShowDebug] = useState(false);

  if (!showDebug) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowDebug(true)}
        className="fixed bottom-4 right-4 z-50"
      >
        🔍 Debug Images
      </Button>
    );
  }

  const imageFields = [
    { key: 'questionImage', label: 'Question Image' },
    { key: 'optionAImage', label: 'Option A Image' },
    { key: 'optionBImage', label: 'Option B Image' },
    { key: 'optionCImage', label: 'Option C Image' },
    { key: 'optionDImage', label: 'Option D Image' },
  ];

  return (
    <Card className="fixed bottom-4 right-4 z-50 p-4 max-w-md max-h-96 overflow-auto bg-white shadow-xl">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-bold">Image Debug Panel</h3>
        <Button variant="ghost" size="sm" onClick={() => setShowDebug(false)}>
          ✕
        </Button>
      </div>

      <div className="space-y-3 text-xs">
        {imageFields.map(({ key, label }) => {
          const value = question?.[key];
          const hasValue = value && value.length > 0;
          const normalizedSrc = hasValue ? normalizeImageSrc(value) : null;

          return (
            <div key={key} className="border-b pb-2">
              <div className="font-semibold text-sm">{label}</div>
              <div className="space-y-1 mt-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${hasValue ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                    {hasValue ? '✓ Present' : '✗ None'}
                  </span>
                  {hasValue && (
                    <span className="text-gray-600">
                      {value.length.toLocaleString()} chars
                    </span>
                  )}
                </div>

                {hasValue && (
                  <>
                    <div className="text-gray-600">
                      <span className="font-medium">Prefix:</span>{' '}
                      <code className="bg-gray-100 px-1 rounded">
                        {value.substring(0, 30)}...
                      </code>
                    </div>

                    <div className="text-gray-600">
                      <span className="font-medium">Suffix:</span>{' '}
                      <code className="bg-gray-100 px-1 rounded">
                        ...{value.substring(value.length - 20)}
                      </code>
                    </div>

                    {normalizedSrc && (
                      <div className="text-gray-600">
                        <span className="font-medium">Normalized:</span>{' '}
                        {normalizedSrc.length.toLocaleString()} chars
                      </div>
                    )}

                    <div className="mt-2 p-2 bg-gray-50 rounded">
                      <div className="text-gray-700 mb-1 font-medium">Preview:</div>
                      <img
                        src={normalizedSrc || undefined}
                        alt={label}
                        className="max-w-full h-auto border border-gray-300 rounded"
                        style={{ maxHeight: '100px' }}
                        onLoad={() => console.log(`✓ ${label} rendered successfully`)}
                        onError={(e) => {
                          console.error(`✗ ${label} failed to render`);
                          e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text x="10" y="50" fill="red">Error</text></svg>';
                        }}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t text-xs text-gray-500">
        <div className="font-semibold mb-1">Tips:</div>
        <ul className="space-y-1 list-disc list-inside">
          <li>Check browser console for detailed logs</li>
          <li>Verify base64 length {'<'} 100KB (~75,000 chars)</li>
          <li>Check Network tab for API response</li>
        </ul>
      </div>
    </Card>
  );
}

/**
 * Usage in test-interface.tsx:
 * 
 * Import:
 * import { ImageDebugPanel } from "@/components/ImageDebugPanel";
 * 
 * Add inside the component (near the question display):
 * <ImageDebugPanel question={currentQuestion} />
 */
