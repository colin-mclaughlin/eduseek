import { useRef, useState } from "react";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Loader2, UploadCloud, FileText } from "lucide-react";

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
  const [isDragOver, setIsDragOver] = useState(false);
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
    setIsDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f && (allowedTypes.includes(f.type) || allowedExts.some(ext => f.name.endsWith(ext)))) {
      setFile(f);
      setError(null);
    } else {
      setFile(null);
      setError("Please select a valid file (.pdf, .docx, .pptx, .txt)");
    }
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
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
      setFile(null);
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
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragOver
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
            : "border-gray-300 hover:border-blue-400 dark:bg-gray-800"
        }`}
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className={`transition-transform duration-200 ${isDragOver ? "scale-110" : ""}`}>
          <UploadCloud className={`mx-auto mb-4 w-12 h-12 ${isDragOver ? "text-blue-500" : "text-gray-400"}`} />
        </div>
        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Drop files here or click to browse</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">Accepted formats: PDF, DOCX, PPTX, TXT</p>
        <Input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          className="hidden"
          onChange={handleFileChange}
        />
        {file && (
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                {file.name}
              </span>
            </div>
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}
      </div>
      <div className="flex justify-end mt-4">
        <Button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="gap-2"
        >
          {uploading && <Loader2 className="animate-spin w-4 h-4" />}
          {uploading ? "Uploading..." : "Upload"}
        </Button>
      </div>
      {result && (
        <Card className="mt-6 p-4 bg-blue-50 dark:bg-gray-900 border border-blue-200 dark:border-blue-800">
          <h2 className="text-lg font-semibold mb-2 text-blue-900 dark:text-blue-100">Summary</h2>
          <p className="mb-4 text-gray-800 dark:text-gray-200">{result.summary}</p>
          <h3 className="font-semibold mb-1 text-blue-900 dark:text-blue-100">Deadlines</h3>
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