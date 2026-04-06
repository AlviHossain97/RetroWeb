import { useState, useCallback } from "react";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function useChatComposer() {
  const [input, setInput] = useState("");
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const [pendingFiles, setPendingFiles] = useState<{ name: string; content: string }[]>([]);

  const addImages = useCallback((files: FileList) => {
    Array.from(files).forEach(file => {
      if (file.size > MAX_FILE_SIZE) {
        console.warn(`[COMPOSER] Skipping ${file.name}: exceeds 10MB limit`);
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        if (base64) {
          setPendingImages(prev => [...prev, base64]);
        }
      };
      reader.onerror = () => {
        console.warn(`[COMPOSER] Failed to read image: ${file.name}`);
      };
      reader.readAsDataURL(file);
    });
  }, []);

  const addFiles = useCallback((files: FileList) => {
    Array.from(files).forEach(file => {
      if (file.size > MAX_FILE_SIZE) {
        console.warn(`[COMPOSER] Skipping ${file.name}: exceeds 10MB limit`);
        return;
      }
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(",")[1];
          if (base64) {
            setPendingImages(prev => [...prev, base64]);
          }
        };
        reader.onerror = () => {
          console.warn(`[COMPOSER] Failed to read image: ${file.name}`);
        };
        reader.readAsDataURL(file);
      } else {
        const reader = new FileReader();
        reader.onload = () => {
          setPendingFiles(prev => [...prev, { name: file.name, content: reader.result as string }]);
        };
        reader.onerror = () => {
          console.warn(`[COMPOSER] Failed to read file: ${file.name}`);
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
