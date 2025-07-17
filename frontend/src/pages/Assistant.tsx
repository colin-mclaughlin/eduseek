import React, { useRef, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose } from "../components/ui/sheet";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
dayjs.extend(relativeTime);
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../components/ui/select";
import UserMessageBubble from "../components/UserMessageBubble";
import EduSeekResponseBubble from "../components/EduSeekResponseBubble";

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
  const [mode, setMode] = useState<'idle' | 'chat'>("idle");
  // Scope state
  const [selectedScope, setSelectedScope] = useState<'all' | 'course' | 'file'>('all');
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);

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

  // Sync legacy state with new state for backward compatibility
  React.useEffect(() => {
    setSelectedScope(scope as 'all' | 'course' | 'file');
    if (scope === 'course') {
      setSelectedCourseId(course || null);
    } else if (scope === 'file') {
      setSelectedFileId(file?.id ? String(file.id) : null);
    }
  }, [scope, course, file]);

  // Scroll to bottom on new message
  React.useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (question: string) => {
    if (!question.trim()) return;
    setError(null);
    setLoading(true);
    setMode("chat");
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
    if (selectedScope === "course" && selectedCourseId) {
      payload.course_id = selectedCourseId;
    } else if (selectedScope === "file" && selectedFileId) {
      payload.file_id = selectedFileId;
    }
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
    setInput("");
    setMode("chat");
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
    <div className="flex flex-col h-[calc(100vh-64px)] min-h-[calc(100vh-64px)] bg-background">
      {/* Scope label above chat */}
      <div className="w-full text-xs text-muted-foreground px-4 pt-2 pb-1 flex items-center gap-2">
        {selectedScope === 'all' && <span>🗂 Searching: All Files</span>}
        {selectedScope === 'course' && selectedCourseId && <span>📘 Searching: {selectedCourseId}</span>}
        {selectedScope === 'file' && selectedFileId && <span>📄 Searching: File #{selectedFileId}</span>}
      </div>
      {/* Chat area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {mode === "idle" && messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center h-full gap-4 text-muted-foreground select-none">
            <div className="text-2xl font-bold mb-4 flex items-center gap-2">
              <span role="img" aria-label="bot">🤖</span> EduSeek Assistant
            </div>
            <div className="flex flex-col gap-3 w-full max-w-xs">
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <Button key={i} variant="outline" size="lg" className="w-full" onClick={() => handlePromptClick(q)} disabled={loading}>
                  {q}
                </Button>
              ))}
            </div>
            <div className="mt-8 text-sm text-center opacity-60">Ask EduSeek anything about your files to get started!</div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-0 py-4 flex flex-col-reverse" style={{scrollbarGutter: 'stable'}}>
            <div ref={chatBottomRef} />
            {messages.slice().reverse().map((msg) =>
              msg.role === "user" ? (
                <UserMessageBubble
                  key={msg.id}
                  content={msg.content}
                  timestamp={dayjs(msg.timestamp).fromNow()}
                />
              ) : (
                <EduSeekResponseBubble
                  key={msg.id}
                  content={msg.content}
                  timestamp={dayjs(msg.timestamp).fromNow()}
                  sources={msg.sources}
                  onOpenFile={handleOpenFile}
                />
              )
            )}
          </div>
        )}
      </div>
      {/* Error */}
      {error && <div className="text-red-500 text-sm mb-2 text-center">{error}</div>}
      {/* Input Bar */}
      <form
        className="flex items-center gap-2 border-t p-3 bg-background sticky bottom-0 z-10"
        onSubmit={e => {
          e.preventDefault();
          if (!loading && input.trim()) handleSend(input.trim());
        }}
      >
        {/* Scope Dropdown */}
        <Select value={scope} onValueChange={setScope} disabled={loading}>
          <SelectTrigger className="w-40 min-w-[8rem]">
            <SelectValue placeholder="Scope" />
          </SelectTrigger>
          <SelectContent>
            {SCOPE_OPTIONS.map(opt => (
              <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {/* Course or File Select if needed */}
        {scope === "course" && (
          <Input
            className="w-36"
            placeholder="Course name..."
            value={course}
            onChange={e => setCourse(e.target.value)}
            disabled={loading}
          />
        )}
        {scope === "file" && (
          <Select
            value={file?.id ? String(file.id) : ""}
            onValueChange={val => {
              const f = files.find(f => String(f.id) === val);
              setFile(f || null);
            }}
            disabled={loading}
          >
            <SelectTrigger className="w-44 min-w-[10rem]">
              <SelectValue placeholder="Select file..." />
            </SelectTrigger>
            <SelectContent>
              {files.map(f => (
                <SelectItem key={f.id} value={String(f.id)}>{f.filename}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Input
          className="flex-1"
          placeholder="Ask EduSeek anything about your files..."
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <Button type="submit" disabled={loading || !input.trim()} className="gap-2">
          {loading && <span className="animate-spin">⏳</span>} Ask
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