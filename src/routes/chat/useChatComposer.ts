import { useState, useCallback } from "react";

export function useChatComposer() {
  const [input, setInput] = useState("");
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const [pendingFiles, setPendingFiles] = useState<{ name: string; content: string }[]>([]);

  const addImages = useCallback((files: FileList) => {
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        setPendingImages(prev => [...prev, base64]);
      };
      reader.readAsDataURL(file);
    });
  }, []);

  const addFiles = useCallback((files: FileList) => {
    Array.from(files).forEach(file => {
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(",")[1];
          setPendingImages(prev => [...prev, base64]);
        };
        reader.readAsDataURL(file);
      } else {
        const reader = new FileReader();
        reader.onload = () => {
          setPendingFiles(prev => [...prev, { name: file.name, content: reader.result as string }]);
        };
        reader.readAsText(file);
      }
    });
  }, []);

  const removePendingImage = useCallback((idx: number) => {
    setPendingImages(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const removePendingFile = useCallback((idx: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const clearComposer = useCallback(() => {
    setInput("");
    setPendingImages([]);
    setPendingFiles([]);
  }, []);

  const hasContent = input.trim().length > 0 || pendingImages.length > 0 || pendingFiles.length > 0;

  return {
    input, setInput,
    pendingImages, pendingFiles,
    addImages, addFiles,
    removePendingImage, removePendingFile,
    clearComposer,
    hasContent,
  };
}
