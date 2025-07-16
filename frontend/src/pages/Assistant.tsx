import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";

interface FileData {
  filename: string;
  summary: string | null;
  deadline: string | null;
}

function isToday(dateStr: string) {
  const today = new Date();
  const d = new Date(dateStr);
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

function isUpcoming(dateStr: string) {
  const today = new Date();
  const d = new Date(dateStr);
  const diff = (d.getTime() - today.setHours(0, 0, 0, 0)) / (1000 * 60 * 60 * 24);
  return diff > 0 && diff <= 3;
}

export default function Assistant() {
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
      .catch(() => {
        setError("Error loading files. Please try again later.");
        setFiles([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const todayTasks = files.filter(f => f.deadline && isToday(f.deadline));
  const upcomingTasks = files.filter(f => f.deadline && isUpcoming(f.deadline));

  return (
    <div className="max-w-2xl mx-auto mt-10 px-2">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <span role="img" aria-label="calendar">📅</span> Today’s Tasks
      </h1>
      {loading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : error ? (
        <div className="text-center text-red-500">{error}</div>
      ) : todayTasks.length > 0 ? (
        <div className="flex flex-col gap-4">
          {todayTasks.map((f, i) => (
            <Card key={f.filename + i} className="border-primary/40">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-medium truncate max-w-xs" title={f.filename}>{f.filename}</CardTitle>
                <span className="text-xs text-amber-700 bg-amber-100 rounded px-2 py-1">Due today</span>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-line mb-2">
                  {f.summary ? f.summary.slice(0, 180) + (f.summary.length > 180 ? "..." : "") : "No summary available."}
                </div>
                <Button size="sm" variant="outline">Ask about this file</Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center text-lg mt-8">
          <span role="img" aria-label="party">🎉</span> Nothing due today! Want to review something?
        </div>
      )}

      {/* Upcoming tasks */}
      {!loading && !error && upcomingTasks.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <span role="img" aria-label="soon">⏳</span> Upcoming Deadlines
          </h2>
          <div className="flex flex-col gap-4">
            {upcomingTasks.map((f, i) => (
              <Card key={f.filename + i} className="border-primary/20">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base font-medium truncate max-w-xs" title={f.filename}>{f.filename}</CardTitle>
                  <span className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1">
                    Due {new Date(f.deadline!).toLocaleDateString(undefined, { month: "long", day: "numeric" })}
                  </span>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-line mb-2">
                    {f.summary ? f.summary.slice(0, 180) + (f.summary.length > 180 ? "..." : "") : "No summary available."}
                  </div>
                  <Button size="sm" variant="outline">Ask about this file</Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Suggestion area */}
      {!loading && !error && todayTasks.length === 0 && files.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <span role="img" aria-label="lightbulb">💡</span> Suggestions
          </h2>
          <div className="flex flex-col gap-4">
            {files.slice(0, 2).map((f, i) => (
              <Card key={f.filename + i} className="border-muted">
                <CardHeader>
                  <CardTitle className="text-base font-medium truncate max-w-xs" title={f.filename}>{f.filename}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-line mb-2">
                    {f.summary ? f.summary.slice(0, 180) + (f.summary.length > 180 ? "..." : "") : "No summary available."}
                  </div>
                  <Button size="sm" variant="outline">Review this file</Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 