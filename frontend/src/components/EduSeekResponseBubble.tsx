import React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SourceChunk {
  file_id: string;
  filename: string;
  chunk_text: string;
  similarity: number;
}

interface EduSeekResponseBubbleProps {
  content: string;
  timestamp: string;
  sources?: SourceChunk[];
  onOpenFile?: (filename: string) => void;
}

const EduSeekResponseBubble: React.FC<EduSeekResponseBubbleProps> = ({ content, timestamp, sources, onOpenFile }) => (
  <div className={cn(
    "flex justify-start mb-2"
  )}>
    <div className="max-w-[75%] bg-muted rounded-lg rounded-bl-none px-4 py-2 shadow-sm">
      <div className="text-sm whitespace-pre-line">{content}</div>
      <div className="text-xs text-muted-foreground mt-1 text-right">{timestamp}</div>
      {sources && sources.length > 0 && (
        <div className="mt-3 space-y-2">
          {sources.map((src, j) => (
            <div key={j} className="p-2 bg-muted-foreground/10 rounded border text-xs">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium">📄 From: {src.filename}</span>
                {onOpenFile && (
                  <Button variant="link" size="sm" className="px-1 py-0 h-6" onClick={() => onOpenFile(src.filename)}>
                    Open file
                  </Button>
                )}
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
);

export default EduSeekResponseBubble; 