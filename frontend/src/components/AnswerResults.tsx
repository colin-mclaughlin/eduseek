import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

export interface AnswerResult {
  chunk: string;
  filename: string;
  score?: number; // 0-1, optional
}

interface AnswerResultsProps {
  results: AnswerResult[];
  loading?: boolean;
  error?: string | null;
}

export const AnswerResults: React.FC<AnswerResultsProps> = ({ results, loading, error }) => {
  if (loading) {
    return (
      <div className="mt-6 w-full flex flex-col gap-3">
        {[1, 2, 3].map(i => (
          <Card key={i} className="animate-pulse opacity-70">
            <CardHeader>
              <CardTitle className="h-4 bg-muted rounded w-1/3 mb-2" />
            </CardHeader>
            <CardContent>
              <div className="h-4 bg-muted rounded w-2/3 mb-2" />
              <div className="h-4 bg-muted rounded w-1/2" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }
  if (error) {
    return <div className="mt-6 text-red-500 text-center">{error}</div>;
  }
  if (!results.length) {
    return <div className="mt-6 text-muted-foreground text-center">No answer found.</div>;
  }
  return (
    <div className="mt-6 w-full flex flex-col gap-3">
      {results.map((res, idx) => (
        <Card key={idx} className="border-primary/40">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base font-medium truncate max-w-xs" title={res.filename}>{res.filename}</CardTitle>
            {typeof res.score === "number" && (
              <span className="text-xs text-muted-foreground font-mono">{Math.round(res.score * 100)}%</span>
            )}
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-line">{res.chunk}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default AnswerResults; 