import React, { useState, useEffect, useCallback } from "react";
import FileSummaryCard from "./FileSummaryCard";
import { Skeleton } from "./ui/skeleton";
import QuestionInput from "./QuestionInput";
import AnswerResults from "./AnswerResults";
import type { AnswerResult } from "./AnswerResults";

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

export const DashboardView: React.FC<{ triggerRefresh?: boolean } > = ({ triggerRefresh }) => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Q&A state
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [qaResults, setQaResults] = useState<AnswerResult[]>([]);

  // Refetch files from backend
  const fetchFiles = useCallback(() => {
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

  // Poll for new files after upload
  const pollFiles = useCallback(() => {
    let count = 0;
    const interval = setInterval(() => {
      fetchFiles();
      count++;
      if (count >= 5) clearInterval(interval);
    }, 2000);
  }, [fetchFiles]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles, triggerRefresh]);

  // Real Q&A handler
  const handleAskQuestion = async (question: string) => {
    setQaLoading(true);
    setQaError(null);
    setQaResults([]);
    try {
      const res = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error("Failed to get answer");
      const data = await res.json();
      // Support both {results: [...]} and direct array
      const results = Array.isArray(data)
        ? data
        : Array.isArray(data.results)
        ? data.results
        : [];
      // Map backend fields to AnswerResult
      setQaResults(
        results.map((r: any) => ({
          chunk: r.content || r.chunk || "",
          filename: r.filename || "",
          score: typeof r.score === "number" ? r.score : undefined,
        }))
      );
    } catch (err: any) {
      setQaError(err.message || "Error getting answer");
      setQaResults([]);
    } finally {
      setQaLoading(false);
    }
  };

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
        <div className="mt-6 text-base text-muted-foreground">Upload a file to start asking questions.</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center w-full max-w-2xl mx-auto mt-8 px-2">
      {/* File summary cards */}
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

      {/* Q&A Section: only show if files exist */}
      {files.length > 0 && (
        <div className="w-full max-w-xl mx-auto mt-12 mb-8">
          <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
            <span role="img" aria-label="brain">🧠</span> Ask about your files
          </h2>
          <QuestionInput onSubmit={handleAskQuestion} loading={qaLoading} />
          <AnswerResults results={qaResults} loading={qaLoading} error={qaError} />
        </div>
      )}
    </div>
  );
};

export default DashboardView; 