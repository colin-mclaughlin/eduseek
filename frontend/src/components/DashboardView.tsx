import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardHeader, CardContent, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import OnQSyncModal from "./OnQSyncModal";
import { useToast } from "./ui/toast";

interface FileData {
  id: number;
  filename: string;
  summary: string | null;
  deadline: string | null;
  deadlines: string[];
}

// function formatDeadline(deadline: string | null): string | null {
//   if (!deadline) return null;
//   const date = new Date(deadline);
//   if (isNaN(date.getTime())) return null;
//   return `Due ${date.toLocaleDateString(undefined, {
//     month: "long",
//     day: "numeric",
//     year: "numeric",
//   })}`;
// }

// Since uploaded_at is not available in the API response,
// we'll sort by filename for now

export const DashboardView: React.FC<{ triggerRefresh?: boolean }> = ({ triggerRefresh }) => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [loadingSuggestion, setLoadingSuggestion] = useState(false);
  const [showOnQModal, setShowOnQModal] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const navigate = useNavigate();
  const { showToast } = useToast();

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
      .catch(() => {
        setError("Error loading files. Please try again later.");
        setFiles([]);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles, triggerRefresh, refreshTrigger]);

  const handleGetSuggestion = async () => {
    setLoadingSuggestion(true);
    try {
      const response = await fetch("http://localhost:8000/api/files/smart-suggestion");
      const data = await response.json();
      setSuggestion(data.suggestion || "No suggestion available right now.");
    } catch (error) {
      console.error("Error fetching suggestion:", error);
      setSuggestion("Failed to load suggestion.");
    } finally {
      setLoadingSuggestion(false);
    }
  };

  const handleOnQSyncSuccess = (results: any) => {
    // Trigger a refresh of the dashboard
    setRefreshTrigger(prev => prev + 1);
    // Show success toast
    showToast(
      `OnQ sync completed! ${results.uploaded || 0} files uploaded successfully.`, 
      "success"
    );
    console.log("OnQ sync completed successfully:", results);
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
  const upcomingDeadlines = files
    .flatMap(file => file.deadlines)
    .map(date => new Date(date))
    .filter(date => date > new Date())
    .sort((a, b) => a.getTime() - b.getTime());
  const upcomingDeadlinesCount = upcomingDeadlines.length;

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
            <div className="text-3xl font-bold">{upcomingDeadlinesCount}</div>
            <p className="text-sm text-muted-foreground mt-1">
              {upcomingDeadlinesCount === 1 ? "deadline" : "deadlines"}
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
            onClick={handleGetSuggestion}
            disabled={summarizedFiles === 0}
          >
            {loadingSuggestion ? "Thinking..." : (summarizedFiles > 0 ? "Give me a suggestion" : "Get file summaries first")}
          </Button>
          
          {suggestion && (
            <div className="mt-4 text-sm text-muted-foreground bg-gray-100 p-4 rounded-lg border">
              💡 {suggestion}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upcoming Deadlines Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            📅 Upcoming Deadlines
          </CardTitle>
        </CardHeader>
        <CardContent>
          {upcomingDeadlines.length > 0 ? (
            <ul className="space-y-2">
              {upcomingDeadlines.slice(0, 5).map((date, index) => (
                <li key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{date.toLocaleDateString()}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {files.find(f => f.deadlines.includes(date.toISOString().split('T')[0]))?.filename || 'Unknown file'}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground text-sm">
              No upcoming deadlines found in your files.
            </p>
          )}
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

      {/* OnQ Sync Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            🎓 Sync from OnQ
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Automatically import all your course files and deadlines from Queen's OnQ platform.
          </p>
          <Button 
            onClick={() => setShowOnQModal(true)}
            className="w-full"
          >
            Sync from OnQ
          </Button>
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

      {/* OnQ Sync Modal */}
      <OnQSyncModal
        isOpen={showOnQModal}
        onClose={() => setShowOnQModal(false)}
        onSuccess={handleOnQSyncSuccess}
      />
    </div>
  );
};

export default DashboardView; 