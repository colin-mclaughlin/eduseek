import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { CalendarDays, FileText, Clock } from "lucide-react";

interface FileSummaryCardProps {
  filename: string;
  summary: string;
  deadline?: string; // ISO date string or undefined
}

// TODO: Replace with ShadCN Collapsible when available in project
export const FileSummaryCard: React.FC<FileSummaryCardProps> = ({
  filename,
  summary,
  deadline,
}) => {
  const [expanded, setExpanded] = useState(false);
  const truncated = summary.length > 180 && !expanded;
  const displaySummary = truncated ? summary.slice(0, 180) + "..." : summary;

  return (
    <Card className="w-full max-w-md mx-auto mb-4 shadow-md">
      <CardHeader className="flex flex-row items-center gap-3 p-4 pb-2">
        <FileText className="text-muted-foreground shrink-0" />
        <div className="flex-1">
          <CardTitle className="text-base break-all">{filename}</CardTitle>
        </div>
        {deadline && (
          <span className="flex items-center gap-1 px-2 py-1 rounded bg-amber-100 text-amber-800 text-xs font-medium">
            <Clock className="w-4 h-4" />
            Due {new Date(deadline).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}
          </span>
        )}
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="text-sm text-muted-foreground whitespace-pre-line">
          {displaySummary}
          {truncated && (
            <button
              className="ml-2 text-blue-600 hover:underline text-xs font-medium"
              onClick={() => setExpanded(true)}
            >
              Read more
            </button>
          )}
          {expanded && summary.length > 180 && (
            <button
              className="ml-2 text-blue-600 hover:underline text-xs font-medium"
              onClick={() => setExpanded(false)}
            >
              Show less
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default FileSummaryCard; 