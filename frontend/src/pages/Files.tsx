import React, { useState, useEffect, useCallback, useMemo } from "react";
import FileUploader from "../components/FileUploader";
import FileCard from "../components/FileCard";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Search, LayoutGrid, List as ListIcon } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "../components/ui/sheet";

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
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [previewFile, setPreviewFile] = useState<FileData | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

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

  // Handle file card click for preview
  const handlePreview = (file: FileData) => {
    setPreviewFile(file);
    setIsSheetOpen(true);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* File Upload Section */}
      <div className="mb-8">
        <FileUploader onUploadSuccess={fetchFiles} />
      </div>

      {/* Search Bar & View Toggle */}
      <div className="mb-6 flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files by name or content..."
            className="pl-10"
          />
          {searchQuery && (
            <p className="text-sm text-muted-foreground mt-2">
              Found {filteredFiles.length} file{filteredFiles.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <div className="ml-4 flex gap-2">
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="icon"
            aria-label="List view"
            onClick={() => setViewMode('list')}
          >
            <ListIcon className="h-5 w-5" />
          </Button>
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="icon"
            aria-label="Grid view"
            onClick={() => setViewMode('grid')}
          >
            <LayoutGrid className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Files List/Grid */}
      {loading ? (
        <div className="text-center text-muted-foreground mt-8">Loading files...</div>
      ) : error ? (
        <div className="text-center text-red-500 mt-8">{error}</div>
      ) : filteredFiles.length === 0 ? (
        <div className="text-center text-muted-foreground mt-8">No files uploaded yet.</div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {filteredFiles.map((file) => (
            <div key={file.id} onClick={() => handlePreview(file)} className="cursor-pointer">
              <FileCard
                file={file}
                onSummarize={handleSummarize}
                onDelete={handleDelete}
                summarizingId={summarizingId}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFiles.map((file) => (
            <div key={file.id} onClick={() => handlePreview(file)} className="cursor-pointer">
              <FileCard
                file={file}
                onSummarize={handleSummarize}
                onDelete={handleDelete}
                summarizingId={summarizingId}
              />
            </div>
          ))}
        </div>
      )}

      {/* File Preview Drawer */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent side="right" className="max-w-md w-full">
          <SheetHeader>
            <SheetTitle>{previewFile?.filename}</SheetTitle>
            <SheetDescription>
              {/* Add file details here */}
              <div className="mt-2">
                <div className="text-xs text-muted-foreground mb-2">
                  Uploaded {previewFile?.uploaded_at}
                </div>
                <div className="mb-4">
                  <strong>Summary:</strong>
                  <div className="mt-1 whitespace-pre-line text-sm">
                    {previewFile?.summary || 'No summary available.'}
                  </div>
                </div>
                <div className="mb-4">
                  <strong>Deadlines:</strong>
                  <ul className="list-disc pl-5 text-sm">
                    {(previewFile?.deadlines ?? []).map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
                <div className="mb-2 text-xs">
                  <span className="font-medium">Type:</span> {previewFile?.filename.split('.').pop()?.toUpperCase()}
                </div>
              </div>
            </SheetDescription>
          </SheetHeader>
          <SheetClose asChild>
            <Button className="mt-4 w-full" variant="outline">Close</Button>
          </SheetClose>
        </SheetContent>
      </Sheet>

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