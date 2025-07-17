import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "./ui/alert-dialog";
import { MoreVertical, Trash2, Calendar } from "lucide-react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

interface FileData {
  id: number;
  filename: string;
  summary: string | null;
  deadline: string | null;
  deadlines?: string[];
  uploaded_at?: string;
}

interface FileCardProps {
  file: FileData;
  onSummarize: (file: FileData) => void;
  onDelete: (fileId: number) => void;
  summarizingId: number | null;
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

export const FileCard: React.FC<FileCardProps> = ({
  file,
  onSummarize,
  onDelete,
  summarizingId,
}) => {
  const [showFullSummary, setShowFullSummary] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fileIcon = getFileIcon(file.filename);
  const uploadTime = file.uploaded_at ? dayjs(file.uploaded_at).fromNow() : 'Recently';
  
  // Handle both single deadline and deadlines array
  const deadlines = file.deadlines || (file.deadline ? [file.deadline] : []);
  const displayDeadlines = deadlines.slice(0, 3);
  const remainingCount = deadlines.length - 3;

  const handleDelete = async () => {
    setIsDeleting(true);
    await onDelete(file.id);
    setIsDeleting(false);
  };

  const summaryText = file.summary || "No summary available.";
  const shouldTruncate = summaryText.length > 200;
  const displaySummary = shouldTruncate && !showFullSummary 
    ? summaryText.slice(0, 200) + "..."
    : summaryText;

  return (
    <Card className="w-full max-w-prose mx-auto hover:shadow-md transition-shadow duration-200">
      <CardHeader className="flex flex-row items-start gap-3 p-4">
        <div className="text-2xl shrink-0">{fileIcon}</div>
        <div className="flex-1 min-w-0">
          <CardTitle className="text-base font-medium truncate" title={file.filename}>
            {file.filename}
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Uploaded {uploadTime}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8"
            onClick={() => alert("Coming soon")}
          >
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="p-4">
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
          
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                size="sm"
                variant="destructive"
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete File</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete <strong>{file.filename}</strong>? 
                  This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="bg-red-600 hover:bg-red-700"
                  disabled={isDeleting}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
};

export default FileCard; 