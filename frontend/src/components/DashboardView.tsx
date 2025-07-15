import React, { useState, useEffect } from "react";
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

export const DashboardView: React.FC = () => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Q&A state
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [qaResults, setQaResults] = useState<AnswerResult[]>([]);

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

  // Mock Q&A handler
  const handleAskQuestion = (question: string) => {
    setQaLoading(true);
    setQaError(null);
    // Simulate async call
    setTimeout(() => {
      // Example mock results
      if (question.toLowerCase().includes("deadline")) {
        setQaResults([
          {
            chunk: "The final project is due July 22, 2025. Please submit via the portal.",
            filename: "CS101_Syllabus.pdf",
            score: 0.92,
          },
          {
            chunk: "Your project proposal is due at the end of week 4.",
            filename: "Project_Proposal.docx",
            score: 0.87,
          },
        ]);
      } else if (question.trim()) {
        setQaResults([
          {
            chunk: "Introduction to computer science, history, and basic concepts.",
            filename: "Lecture_Notes_Week1.txt",
            score: 0.81,
          },
        ]);
      } else {
        setQaResults([]);
      }
      setQaLoading(false);
    }, 900);
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