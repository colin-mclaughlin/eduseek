import React, { useState, useEffect, useCallback } from "react";
import FileUploader from "../components/FileUploader";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";

interface FileData {
  id: number;
  filename: string;
  summary: string | null;
  deadline: string | null;
}

export default function Files() {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summarizingId, setSummarizingId] = useState<number | null>(null);

  const fetchFiles = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch("http://localhost:8000/api/files/")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to fetch files");
        const data = await res.json();
        setFiles(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        setError("Error loading files. Please try again later.");
        setFiles([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSummarize = async (file: FileData) => {
    if (!file || typeof file.id !== 'number') {
      console.error("Invalid file ID:", file?.id);
      return;
    }
    setSummarizingId(file.id);
    try {
      const res = await fetch(`http://localhost:8000/api/files/summarize/${file.id}`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        setFiles(prev => prev.map(f => (f.id === updated.id ? { ...f, summary: updated.summary } : f)));
      }
    } catch (e) {
      // Optionally show error
    } finally {
      setSummarizingId(null);
    }
  };

  const handleDelete = async (fileId: number) => {
    const res = await fetch(`http://localhost:8000/api/files/${fileId}`, { method: "DELETE" });
    if (res.ok) {
      setFiles(prev => prev.filter(file => file.id !== fileId));
    } else {
      console.error("Failed to delete file:", await res.text());
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  return (
    <div>
      <FileUploader onUploadSuccess={fetchFiles} />
      {loading ? (
        <div className="text-center text-muted-foreground mt-8">Loading files...</div>
      ) : error ? (
        <div className="text-center text-red-500 mt-8">{error}</div>
      ) : files.length === 0 ? (
        <div className="text-center text-muted-foreground mt-8">No files uploaded yet.</div>
      ) : (
        <div className="max-w-2xl mx-auto mt-8 flex flex-col gap-4">
          {(files ?? []).map((f) => (
            <Card key={f.id}>
              <CardHeader>
                <CardTitle className="text-base font-medium truncate max-w-xs" title={f.filename}>{f.filename}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-line mb-2">
                  {f.summary ? f.summary.slice(0, 180) + (f.summary.length > 180 ? "..." : "") : "No summary available."}
                </div>
                {f.deadline && (
                  <span className="text-xs text-amber-700 bg-amber-100 rounded px-2 py-1">Due {new Date(f.deadline).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}</span>
                )}
                <div className="flex gap-2 mt-2">
                  {!f.summary && (
                    <Button
                      size="sm"
                      className="mt-0"
                      disabled={summarizingId === f.id}
                      onClick={() => handleSummarize(f)}
                    >
                      {summarizingId === f.id ? "Summarizing..." : "Summarize"}
                    </Button>
                  )}
                  <Button
                    size="sm"
                    className="bg-red-500 hover:bg-red-600 text-white mt-0"
                    onClick={() => handleDelete(f.id)}
                  >
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
} 