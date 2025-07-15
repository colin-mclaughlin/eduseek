import React, { useState, useEffect } from "react";
import FileSummaryCard from "./FileSummaryCard";
import { Skeleton } from "./ui/skeleton";

interface FileData {
  filename: string;
  summary: string | null;
  deadline: string | null;
}

function formatDeadline(deadline: string | null): string | null {
  if (!deadline) return null;
  const date = new Date(deadline);
  if (isNaN(date.getTime())) return null;
  return `Due ${date.toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  })}`;
}

export const DashboardView: React.FC = () => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch("http://localhost:8000/api/files")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to fetch files");
        const data = await res.json();
        setFiles(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError("Error loading files. Please try again later.");
        setFiles([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    // Skeleton loader for 3 cards
    return (
      <div className="flex flex-col items-center gap-4 w-full max-w-2xl mx-auto mt-8">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="w-full max-w-md h-32 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center text-red-500">
        <div className="text-lg font-medium">{error}</div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
        <div className="text-4xl mb-2">📂</div>
        <div className="text-lg font-medium">No files uploaded yet</div>
        <div className="text-sm mt-1">Upload files to see their summaries and deadlines here.</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center w-full max-w-2xl mx-auto mt-8 px-2">
      {files.map((file, idx) => {
        const formattedDeadline = formatDeadline(file.deadline) || undefined;
        return (
          <FileSummaryCard
            key={file.filename + idx}
            filename={file.filename}
            summary={file.summary || "No summary available."}
            deadline={formattedDeadline}
          />
        );
      })}
    </div>
  );
};

export default DashboardView; 