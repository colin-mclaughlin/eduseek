import React, { useState, useRef, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from "./ui/dropdown-menu";
import { MoreVertical, Trash2, Calendar, Download, Pencil, Eye, Globe } from "lucide-react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { cn } from "../lib/utils";

dayjs.extend(relativeTime);

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

interface FileCardProps {
  file: FileData;
  onSummarize: (file: FileData) => void;
  onDelete: (fileId: number) => void;
  summarizingId: number | null;
  onPreview?: (file: FileData) => void;
  onRename?: (id: number, newName: string) => void;
}

const getFileIcon = (filename: string): string => {
  const extension = filename.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'pdf':
      return '📑';
    case 'docx':
    case 'doc':
      return '📄';
    case 'txt':
      return '📃';
    case 'pptx':
    case 'ppt':
      return '📊';
    case 'xlsx':
    case 'xls':
      return '📈';
    default:
      return '📄';
  }
};

const formatDeadline = (deadline: string): string => {
  const date = dayjs(deadline);
  return date.format('MMM D');
};

// Update the saveRenamedFile function to call backend
const saveRenamedFile = async (id: number, newName: string): Promise<boolean> => {
  try {
    // Validate filename
    if (!newName.trim()) {
      throw new Error("Filename cannot be empty");
    }
    
    const filename = newName.trim();
    
    const res = await fetch(`http://localhost:800/api/files/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || "Failed to rename file");
    }
    
    return true;
  } catch (error: any) {
    console.error("Rename error:", error);
    throw error;
  }
};

export const FileCard: React.FC<FileCardProps> = ({
  file,
  onSummarize,
  onDelete,
  summarizingId,
  onPreview,
  onRename,
}) => {
  const [showFullSummary, setShowFullSummary] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [newName, setNewName] = useState(file.filename);
  const [renameError, setRenameError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [renaming]);

  const fileIcon = getFileIcon(file.filename);
  const uploadTime = file.uploaded_at ? dayjs(file.uploaded_at).fromNow() : 'Recently';
  const deadlines = file.deadlines || (file.deadline ? [file.deadline] : []);
  const displayDeadlines = deadlines.slice(0, 3);
  const remainingCount = deadlines.length - 3;

  // Handle tags display
  const tags = file.tags || [];
  const displayTags = tags.slice(0, 3);
  const remainingTags = tags.length - 3;

  const handleDelete = async () => {
    setIsDeleting(true);
    await onDelete(file.id);
    setIsDeleting(false);
  };

  const handleRename = async () => {
    if (!newName.trim() || newName === file.filename) {
      setRenaming(false);
      return;
    }
    
    setIsRenaming(true);
    setRenameError(null);
    
    try {
      await saveRenamedFile(file.id, newName);
      if (onRename) onRename(file.id, newName);
      setRenaming(false);
      // Show success message (you can add toast here later)
      console.log("File renamed successfully");
    } catch (error: any) {
      setRenameError(error.message || "Failed to rename file");
      setNewName(file.filename); // Revert to original name
      setRenaming(false);
      // Show error message (you can add toast here later)
      console.error("Rename failed:", error.message);
    } finally {
      setIsRenaming(false);
    }
  };

  const handleRenameKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isRenaming) {
      handleRename();
    } else if (e.key === 'Escape') {
      setRenaming(false);
      setNewName(file.filename);
      setRenameError(null);
    }
  };

  const summaryText = file.summary || "No summary available.";
  const shouldTruncate = summaryText.length > 200;
  const displaySummary = shouldTruncate && !showFullSummary 
    ? summaryText.slice(0, 200) + "..."
    : summaryText;

  // Download stub (replace with real link if available)
  const handleDownload = () => {
    alert("Download coming soon (or implement real link)");
  };

  // Open With stub
  const handleOpenWith = (app: string) => {
    alert(`Open with ${app} coming soon`);
  };

  return (
    <Card className="w-full max-w-prose mx-auto hover:shadow-md transition-shadow duration-200 relative">
      <CardHeader className="flex flex-row items-start gap-3 p-4 pb-2">
        <div className="text-2xl shrink-0">{fileIcon}</div>
        <div className="flex-1 min-w-0">
          {renaming ? (
            <div className="space-y-1">
              <input
                ref={inputRef}
                className={cn(
                  "text-base font-medium truncate bg-background border rounded px-2 py-1 w-full focus:outline-none focus:ring",
                  isRenaming && "opacity-50 cursor-not-allowed",
                  renameError && "border-red-500"
                )}
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onBlur={handleRename}
                onKeyDown={handleRenameKey}
                maxLength={128}
                disabled={isRenaming}
              />
              {renameError && (
                <p className="text-xs text-red-600">{renameError}</p>
              )}
            </div>
          ) : (
            <CardTitle
              className="text-base font-medium truncate cursor-pointer"
              title={file.filename}
              onClick={() => setRenaming(true)}
            >
              {newName}
            </CardTitle>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            Uploaded {uploadTime}
          </p>
          
          {/* Tags Display */}
          {displayTags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {displayTags.map((tag, index) => (
                <span
                  key={index}
                  className="bg-muted text-xs px-2 py-0.5 rounded-full text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
              {remainingTags > 0 && (
                <span className="bg-muted text-xs px-2 py-0.5 rounded-full text-muted-foreground">
                  +{remainingTags} more
                </span>
              )}
            </div>
          )}
        </div>
        {/* Dropdown Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onPreview && onPreview(file)}>
              <Eye className="h-4 w-4 mr-2" /> Preview
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setRenaming(true)}>
              <Pencil className="h-4 w-4 mr-2" /> Rename
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" /> Download
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <Globe className="h-4 w-4 mr-2" /> Open With...
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem disabled onClick={() => handleOpenWith('Google Docs')}>Google Docs</DropdownMenuItem>
                <DropdownMenuItem disabled={file.filename.split('.').pop()?.toLowerCase() !== 'txt'} onClick={() => handleOpenWith('Notepad')}>Notepad</DropdownMenuItem>
                <DropdownMenuItem disabled onClick={() => handleOpenWith('Word')}>Word</DropdownMenuItem>
                <DropdownMenuItem disabled onClick={() => handleOpenWith('LMS')}>Open in LMS</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleDelete} className="text-red-600">
              <Trash2 className="h-4 w-4 mr-2" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="text-sm text-muted-foreground whitespace-pre-line mb-3">
          {displaySummary}
          {shouldTruncate && (
            <button
              className="ml-2 text-blue-600 hover:underline text-xs font-medium"
              onClick={() => setShowFullSummary(!showFullSummary)}
            >
              {showFullSummary ? "Show less" : "Show more"}
            </button>
          )}
        </div>
        {/* Deadline Pills */}
        {displayDeadlines.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {displayDeadlines.map((deadline, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs"
              >
                <Calendar className="h-3 w-3" />
                {formatDeadline(deadline)}
              </span>
            ))}
            {remainingCount > 0 && (
              <span className="inline-flex items-center rounded-full bg-muted px-2">
                +{remainingCount} more
              </span>
            )}
          </div>
        )}
        <div className="flex gap-2">
          {!file.summary && (
            <Button
              size="sm"
              disabled={summarizingId === file.id}
              onClick={() => onSummarize(file)}
            >
              {summarizingId === file.id ? "Summarizing..." : "Summarize"}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default FileCard; 