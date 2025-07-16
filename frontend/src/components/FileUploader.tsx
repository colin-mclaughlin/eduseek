import { useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, UploadCloud } from "lucide-react";

interface Deadline {
  title: string;
  due_date: string;
  type: string;
}

interface UploadResult {
  summary: string;
  deadlines: Deadline[];
}

interface FileUploaderProps {
  onUploadSuccess?: () => void;
}

export default function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
  ];
  const allowedExts = [".pdf", ".docx", ".pptx", ".txt"];

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f && (allowedTypes.includes(f.type) || allowedExts.some(ext => f.name.endsWith(ext)))) {
      setFile(f);
      setError(null);
    } else {
      setFile(null);
      setError("Please select a valid file (.pdf, .docx, .pptx, .txt)");
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f && (allowedTypes.includes(f.type) || allowedExts.some(ext => f.name.endsWith(ext)))) {
      setFile(f);
      setError(null);
    } else {
      setFile(null);
      setError("Please select a valid file (.pdf, .docx, .pptx, .txt)");
    }
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("http://localhost:8000/api/files/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setResult(data);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card className="p-6 mb-6 max-w-xl mx-auto">
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-400 transition-colors bg-gray-50 dark:bg-gray-800"
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
      >
        <UploadCloud className="mx-auto mb-2 w-8 h-8 text-blue-500" />
        <p className="mb-2 text-gray-700 dark:text-gray-200">Drag and drop a file here, or click to select</p>
        <Input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          className="hidden"
          onChange={handleFileChange}
        />
        {file && <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">Selected: {file.name}</div>}
        {error && <div className="mt-2 text-sm text-red-600">{error}</div>}
      </div>
      <div className="flex justify-end mt-4">
        <Button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="gap-2"
        >
          {uploading && <Loader2 className="animate-spin w-4 h-4" />}
          Upload
        </Button>
      </div>
      {result && (
        <Card className="mt-6 p-4 bg-blue-50 dark:bg-gray-900">
          <h2 className="text-lg font-semibold mb-2">Summary</h2>
          <p className="mb-4 text-gray-800 dark:text-gray-200">{result.summary}</p>
          <h3 className="font-semibold mb-1">Deadlines</h3>
          <ul className="list-disc pl-5 space-y-1">
            {(result.deadlines ?? []).map((d, i) => (
              <li key={i} className="text-gray-700 dark:text-gray-300">
                <span className="font-medium">{d.title}</span> — {d.due_date} <span className="italic text-xs">({d.type})</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </Card>
  );
} 