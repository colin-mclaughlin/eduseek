import React, { useState, useEffect, useCallback, useMemo } from "react";
import FileUploader from "../components/FileUploader";
import FileCard from "../components/FileCard";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Search } from "lucide-react";

interface FileData {
  id: number;
  filename: string;
  summary: string | null;
  deadline: string | null;
  deadlines?: string[];
  uploaded_at?: string;
}

export default function Files() {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summarizingId, setSummarizingId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

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

  const handleAsk = async () => {
    setAsking(true);
    setAnswer("");
    const res = await fetch("http://localhost:8000/api/files/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (res.ok) {
      const data = await res.json();
      setAnswer(data.answer);
    } else {
      setAnswer("Query failed: " + (await res.text()));
    }
    setAsking(false);
  };

  // Filter files based on search query
  const filteredFiles = useMemo(() => {
    if (!searchQuery.trim()) return files;
    
    const query = searchQuery.toLowerCase();
    return files.filter(file => 
      file.filename.toLowerCase().includes(query) ||
      (file.summary && file.summary.toLowerCase().includes(query))
    );
  }, [files, searchQuery]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* File Upload Section */}
      <div className="mb-8">
        <FileUploader onUploadSuccess={fetchFiles} />
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files by name or content..."
            className="pl-10"
          />
        </div>
        {searchQuery && (
          <p className="text-sm text-muted-foreground mt-2">
            Found {filteredFiles.length} file{filteredFiles.length !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Files List */}
      {loading ? (
        <div className="text-center text-muted-foreground mt-8">Loading files...</div>
      ) : error ? (
        <div className="text-center text-red-500 mt-8">{error}</div>
      ) : filteredFiles.length === 0 ? (
        <div className="text-center text-muted-foreground mt-8">No files uploaded yet.</div>
      ) : (
        <div className="space-y-4">
          {filteredFiles.map((file) => (
            <FileCard
              key={file.id}
              file={file}
              onSummarize={handleSummarize}
              onDelete={handleDelete}
              summarizingId={summarizingId}
            />
          ))}
        </div>
      )}

      {/* Q&A Section */}
      <div className="mt-12 border-t pt-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Ask About Your Files</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="Ask a question about your uploaded files..."
              disabled={asking}
            />
            <Button 
              onClick={handleAsk} 
              disabled={asking || !question.trim()} 
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {asking ? "Asking..." : "Ask Question"}
            </Button>
            {answer && (
              <div className="mt-4 p-4 border rounded-lg bg-muted/50">
                <p className="font-medium text-sm text-muted-foreground mb-2">Answer:</p>
                <p className="whitespace-pre-line">{answer}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 