import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardHeader, CardContent, CardTitle } from "./ui/card";
import { Button } from "./ui/button";

interface FileData {
  id: number;
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

// Since uploaded_at is not available in the API response,
// we'll sort by filename for now

export const DashboardView: React.FC<{ triggerRefresh?: boolean }> = ({ triggerRefresh }) => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

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

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles, triggerRefresh]);

  const handleGiveSuggestion = () => {
    navigate("/assistant");
  };

  if (loading) {
    return (
      <div className="w-full max-w-4xl mx-auto p-6">
        <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
          <div className="text-lg font-medium">Loading your dashboard...</div>
        </div>
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

  const summarizedFiles = files.filter(f => f.summary).length;
  const upcomingDeadlines = files.filter(f => f.deadline && new Date(f.deadline) > new Date()).length;

  if (files.length === 0) {
    return (
      <div className="w-full max-w-4xl mx-auto p-6">
        <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
          <div className="text-4xl mb-2">📂</div>
          <div className="text-lg font-medium">No files uploaded yet</div>
          <div className="text-sm mt-1">Upload files to see your academic dashboard here.</div>
          <Button 
            className="mt-6" 
            onClick={() => navigate("/files")}
          >
            Upload Your First File
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto p-6 space-y-6">
      {/* Smart Overview Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              📁 Total Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{files.length}</div>
            <p className="text-sm text-muted-foreground mt-1">
              {files.length === 1 ? "file uploaded" : "files uploaded"}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              🧠 Summarized Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summarizedFiles}</div>
            <p className="text-sm text-muted-foreground mt-1">
              {summarizedFiles === 1 ? "file processed" : "files processed"}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              📅 Upcoming Deadlines
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{upcomingDeadlines}</div>
            <p className="text-sm text-muted-foreground mt-1">
              {upcomingDeadlines === 1 ? "deadline" : "deadlines"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Daily Assistant Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            🧠 What should I do today?
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 mb-4">
            You have {files.length} uploaded {files.length === 1 ? "file" : "files"}. 
            {summarizedFiles > 0 ? (
              <>
                {" "}Would you like a study suggestion based on your {summarizedFiles} summarized {summarizedFiles === 1 ? "lecture" : "lectures"}?
              </>
            ) : (
              " Start by getting summaries of your uploaded files to unlock personalized study suggestions."
            )}
          </p>
          <Button 
            variant="default" 
            onClick={handleGiveSuggestion}
            disabled={summarizedFiles === 0}
          >
            {summarizedFiles > 0 ? "Give me a suggestion" : "Get file summaries first"}
          </Button>
        </CardContent>
      </Card>

      {/* Recent Activity Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            🕓 Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {files.length > 0 ? (
                         <ul className="space-y-2">
               {files
                 .sort((a, b) => a.filename.localeCompare(b.filename))
                 .slice(0, 5)
                 .map((file, index) => (
                   <li key={file.id || index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                     <div className="flex items-center gap-2">
                       <span className="text-sm font-medium">{file.filename}</span>
                       {file.summary && (
                         <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                           summarized
                         </span>
                       )}
                     </div>
                     <div className="text-xs text-muted-foreground">
                       {file.summary ? "Processed" : "Uploaded"}
                     </div>
                   </li>
                 ))}
             </ul>
          ) : (
            <p className="text-muted-foreground">No recent activity</p>
          )}
        </CardContent>
      </Card>

      {/* Quick Access Shortcuts */}
      <div className="grid grid-cols-2 gap-4">
        <Button 
          variant="outline" 
          onClick={() => navigate("/files")}
          className="h-12"
        >
          📂 View Files
        </Button>
        <Button 
          variant="outline" 
          onClick={() => navigate("/assistant")}
          className="h-12"
        >
          🤖 Ask EduSeek
        </Button>
        <Button 
          variant="outline" 
          disabled
          className="h-12"
        >
          📅 Calendar (coming soon)
        </Button>
        <Button 
          variant="outline" 
          disabled
          className="h-12"
        >
          ⚙️ Settings (coming soon)
        </Button>
      </div>
    </div>
  );
};

export default DashboardView; 