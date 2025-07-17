import React, { useRef, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose } from "../components/ui/sheet";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
dayjs.extend(relativeTime);

interface SourceChunk {
  file_id: string;
  filename: string;
  chunk_text: string;
  similarity: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  sources?: SourceChunk[];
}

interface FileData {
  id: number;
  filename: string;
  summary: string | null;
  deadline: string | null;
  deadlines?: string[];
  uploaded_at?: string;
  size?: number;
  source?: string;
  tags?: string[];
}

const SUGGESTED_QUESTIONS = [
  "What’s due this week?",
  "Summarize all of CISC 235",
  "What topics should I review?",
  "List all upcoming deadlines",
  "Give me a study plan for this week"
];

const SCOPE_OPTIONS = [
  { label: "All Files", value: "all" },
  { label: "Specific Course", value: "course" },
  { label: "Single File", value: "file" }
];

export default function Assistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState("all");
  const [course, setCourse] = useState("");
  const [file, setFile] = useState<FileData | null>(null);
  const [files, setFiles] = useState<FileData[]>([]);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<FileData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Fetch files for scope selection and preview
  React.useEffect(() => {
    fetch("http://localhost:8000/api/files")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to fetch files");
        const data = await res.json();
        setFiles(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        setFiles([]);
      });
  }, []);

  // Scroll to bottom on new message
  React.useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (question: string) => {
    if (!question.trim()) return;
    setError(null);
    setLoading(true);
    const userMsg: ChatMessage = {
      id: Math.random().toString(36).slice(2),
      role: "user",
      content: question,
      timestamp: Date.now(),
    };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput("");
    // Prepare payload
    let payload: any = { query: question };
    if (scope === "course" && course) payload.course_filter = course;
    if (scope === "file" && file) payload.course_filter = file.filename;
    try {
      const res = await fetch("http://localhost:8000/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Query failed");
      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: Math.random().toString(36).slice(2),
        role: "assistant",
        content: data.answer,
        timestamp: Date.now(),
        sources: data.sources || [],
      };
      setMessages((msgs) => [...msgs, assistantMsg]);
    } catch (e: any) {
      setError(e.message || "Failed to get answer");
      setMessages((msgs) => [
        ...msgs,
        {
          id: Math.random().toString(36).slice(2),
          role: "assistant",
          content: "Sorry, I couldn't get an answer. Please try again.",
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt: string) => {
    setInput(prompt);
    handleSend(prompt);
  };

  const handleOpenFile = (filename: string) => {
    const f = files.find(f => f.filename === filename);
    if (f) {
      setPreviewFile(f);
      setIsSheetOpen(true);
    }
  };

  return (
    <div className="max-w-2xl mx-auto flex flex-col h-[calc(100vh-4rem)] pt-6 pb-2 px-2">
      <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <span role="img" aria-label="bot">🤖</span> EduSeek Assistant
      </h1>
      <div className="mb-3 flex flex-wrap gap-2">
        {SUGGESTED_QUESTIONS.map((q, i) => (
          <Button key={i} variant="outline" size="sm" onClick={() => handlePromptClick(q)} disabled={loading}>
            {q}
          </Button>
        ))}
      </div>
      {/* Scope Selector */}
      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm font-medium">Search scope:</span>
        <div className="flex gap-2">
          {SCOPE_OPTIONS.map(opt => (
            <Button
              key={opt.value}
              variant={scope === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => setScope(opt.value)}
              disabled={loading}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        {scope === "course" && (
          <Input
            className="ml-2 w-36"
            placeholder="Course name..."
            value={course}
            onChange={e => setCourse(e.target.value)}
            disabled={loading}
          />
        )}
        {scope === "file" && (
          <select
            className="ml-2 border rounded px-2 py-1 text-sm"
            value={file?.id || ""}
            onChange={e => {
              const f = files.find(f => f.id === Number(e.target.value));
              setFile(f || null);
            }}
            disabled={loading}
          >
            <option value="">Select file...</option>
            {files.map(f => (
              <option key={f.id} value={f.id}>{f.filename}</option>
            ))}
          </select>
        )}
      </div>
      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto bg-muted/50 rounded-lg p-4 mb-2 border">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground mt-16">Ask EduSeek anything about your files to get started!</div>
        )}
        {messages.map((msg, i) => (
          <div key={msg.id} className={`flex mb-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] rounded-lg px-4 py-2 shadow-sm ${msg.role === "user" ? "bg-primary text-primary-foreground rounded-br-none" : "bg-muted rounded-bl-none"}`}>
              <div className="text-sm whitespace-pre-line">{msg.content}</div>
              <div className="text-xs text-muted-foreground mt-1 text-right">
                {dayjs(msg.timestamp).fromNow()}
              </div>
              {/* Source highlights for assistant */}
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.sources.map((src, j) => (
                    <div key={j} className="p-2 bg-muted-foreground/10 rounded border text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">📄 From: {src.filename}</span>
                        <Button variant="link" size="sm" className="px-1 py-0 h-6" onClick={() => handleOpenFile(src.filename)}>
                          Open file
                        </Button>
                        {typeof src.similarity === "number" && (
                          <span className="ml-auto text-[10px] text-muted-foreground">sim: {src.similarity}</span>
                        )}
                      </div>
                      <code className="block text-muted-foreground bg-background rounded p-1 overflow-x-auto">{src.chunk_text}</code>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={chatBottomRef} />
      </div>
      {/* Error */}
      {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
      {/* Input Bar */}
      <form
        className="flex gap-2 items-center border-t pt-3 bg-background sticky bottom-0"
        onSubmit={e => {
          e.preventDefault();
          if (!loading && input.trim()) handleSend(input.trim());
        }}
      >
        <Input
          className="flex-1"
          placeholder="Ask EduSeek anything about your files..."
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          {loading ? <span className="animate-spin mr-2">⏳</span> : null} Ask
        </Button>
      </form>
      {/* File Preview Drawer */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent side="right" className="max-w-md w-full">
          <SheetHeader>
            <SheetTitle>
              {previewFile ? previewFile.filename : ''}
            </SheetTitle>
            <SheetDescription>
              {previewFile && (
                <div className="mt-2 space-y-4">
                  {/* Metadata */}
                  <div className="flex flex-col gap-1 text-xs text-muted-foreground mb-2">
                    <div>
                      <span className="font-medium">Uploaded:</span> {previewFile.uploaded_at ? dayjs(previewFile.uploaded_at).fromNow() : 'Unknown'}
                    </div>
                    {previewFile.size && (
                      <div>
                        <span className="font-medium">Size:</span> {Math.round(previewFile.size / 1024)} KB
                      </div>
                    )}
                    <div>
                      <span className="font-medium">Source:</span> {previewFile.source === 'lms' ? 'Synced from LMS' : 'Uploaded manually'}
                    </div>
                    <div>
                      <span className="font-medium">Deadlines:</span> {(previewFile.deadlines?.length || 0)}
                    </div>
                  </div>
                  {/* Summary */}
                  <div className="mb-4">
                    <strong>Summary:</strong>
                    <div className="mt-1 whitespace-pre-line text-sm">
                      {previewFile.summary || 'No summary available.'}
                    </div>
                  </div>
                  {/* Tags */}
                  {previewFile.tags && previewFile.tags.length > 0 && (
                    <div className="mb-4">
                      <strong>Tags:</strong>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {previewFile.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="bg-muted text-xs px-2 py-1 rounded-full text-muted-foreground"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Deadlines */}
                  <div className="mb-4">
                    <strong>Deadlines:</strong>
                    <ul className="list-disc pl-5 text-sm">
                      {(previewFile.deadlines ?? []).map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </SheetDescription>
          </SheetHeader>
          <SheetClose asChild>
            <Button className="mt-4 w-full" variant="outline">Close</Button>
          </SheetClose>
        </SheetContent>
      </Sheet>
    </div>
  );
} 