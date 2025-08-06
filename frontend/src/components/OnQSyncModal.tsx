import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardHeader, CardContent, CardTitle } from "./ui/card";
import { useToast } from "./ui/toast";

interface OnQSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (results: any) => void;
}

interface SyncStatus {
  is_running: boolean;
  current_step: string;
  progress: number;
  message: string;
  error: string | null;
  results: any;
  job_id: string | null;
  twofa_number?: string | null;
}

export default function OnQSyncModal({ isOpen, onClose, onSuccess }: OnQSyncModalProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();

  // Poll for sync status when sync is running
  useEffect(() => {
    if (!syncStatus?.is_running) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch("http://localhost:8000/api/sync_lms/status");
        const status: SyncStatus = await response.json();
        setSyncStatus(status);

        // If sync completed successfully
        if (!status.is_running && status.current_step === "completed" && status.results) {
          clearInterval(pollInterval);
          showToast(
            `OnQ sync completed! ${status.results.uploaded || 0} files uploaded successfully.`,
            "success"
          );
          if (onSuccess) {
            onSuccess(status.results);
          }
          // Auto-close modal after 3 seconds on success
          setTimeout(() => {
            handleClose();
          }, 3000);
        }
        
        // If sync failed
        if (!status.is_running && status.error) {
          clearInterval(pollInterval);
          setError(status.error);
          showToast(`OnQ sync failed: ${status.error}`, "error");
        }
      } catch (err) {
        console.error("Error polling sync status:", err);
        clearInterval(pollInterval);
        setError("Failed to check sync status");
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [syncStatus?.is_running, onSuccess]);

  const handleStartSync = async () => {
    if (!username || !password) {
      setError("Please enter both username and password");
      return;
    }

    setIsStarting(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/sync_lms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to start sync");
      }

      // Start polling for status
      setSyncStatus({
        is_running: true,
        current_step: "initializing",
        progress: 0,
        message: "Starting OnQ sync...",
        error: null,
        results: null,
        job_id: data.job_id,
      });
    } catch (err: any) {
      setError(err.message || "Failed to start sync");
    } finally {
      setIsStarting(false);
    }
  };

  const handleClose = () => {
    setUsername("");
    setPassword("");
    setSyncStatus(null);
    setError(null);
    setIsStarting(false);
    onClose();
  };

  const getStepIcon = (step: string) => {
    switch (step) {
      case "initializing": return "⚡";
      case "login": return "🔑";
      case "awaiting_2fa": return "📱";
      case "login_complete": return "✅";
      case "scraping": return "📁";
      case "processing": return "⚙️";
      case "ingesting": return "📥";
      case "completed": return "✅";
      case "error": return "❌";
      default: return "⏳";
    }
  };

  const getStepDescription = (step: string) => {
    switch (step) {
      case "initializing": return "Preparing sync process";
      case "login": return "Logging into OnQ";
      case "awaiting_2fa": return "Waiting for two-factor authentication";
      case "login_complete": return "Login completed successfully";
      case "scraping": return "Scanning for course files";
      case "processing": return "Processing found files";
      case "ingesting": return "Uploading to EduSeek";
      case "completed": return "Sync completed successfully";
      case "error": return "Sync failed";
      default: return "Working...";
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center">
          <CardTitle className="text-xl flex items-center justify-center gap-2">
            🎓 Sync from OnQ
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Securely log in to OnQ, fetch your courses, and automatically import all files and deadlines
          </p>
        </CardHeader>
        <CardContent>
          {!syncStatus ? (
            // Initial form
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">OnQ Username (NetID)</label>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your NetID"
                  disabled={isStarting}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">OnQ Password</label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  disabled={isStarting}
                />
              </div>
              <div className="text-xs text-muted-foreground bg-blue-50 p-3 rounded-lg">
                🔒 Your credentials are only used for this sync and are never stored
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleClose}
                  disabled={isStarting}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleStartSync}
                  disabled={isStarting || !username || !password}
                  className="flex-1"
                >
                  {isStarting ? "Starting..." : "Start Sync"}
                </Button>
              </div>
            </div>
          ) : (
            // Progress display
            <div className="space-y-4">
              <div className="text-center">
                <div className="text-4xl mb-2">{getStepIcon(syncStatus.current_step)}</div>
                <div className="text-lg font-medium">{getStepDescription(syncStatus.current_step)}</div>
                <div className="text-sm text-muted-foreground mt-1">{syncStatus.message}</div>
              </div>
              
              {/* 2FA Number Display */}
              {syncStatus.twofa_number && (
                <div className="bg-yellow-50 border-2 border-yellow-300 p-4 rounded-lg">
                  <div className="text-center">
                    <div className="text-lg font-bold text-yellow-800 mb-2">
                      Two-Factor Authentication Required
                    </div>
                    <div className="text-sm text-yellow-700 mb-3">
                      Enter this number in your Microsoft Authenticator app:
                    </div>
                    <div className="text-3xl font-bold text-yellow-900 bg-yellow-100 px-4 py-2 rounded-lg inline-block">
                      {syncStatus.twofa_number}
                    </div>
                    <div className="text-xs text-yellow-600 mt-2">
                      Waiting for you to approve the sign-in on your phone...
                    </div>
                  </div>
                </div>
              )}
              
              {syncStatus.is_running && (
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${syncStatus.progress}%` }}
                  />
                </div>
              )}

              {syncStatus.results && (
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-sm font-medium text-green-800 mb-2">Sync Results:</div>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>📁 {syncStatus.results.files?.length || 0} files found</li>
                    <li>✅ {syncStatus.results.uploaded || 0} files uploaded</li>
                    <li>⏭️ {syncStatus.results.duplicates || 0} duplicates skipped</li>
                    {syncStatus.results.failed > 0 && (
                      <li>❌ {syncStatus.results.failed} files failed</li>
                    )}
                  </ul>
                  {syncStatus.results.course_name && (
                    <div className="text-sm text-green-600 mt-2">
                      Course: {syncStatus.results.course_name}
                    </div>
                  )}
                </div>
              )}

              {!syncStatus.is_running && syncStatus.current_step === "completed" && (
                <Button onClick={handleClose} className="w-full">
                  Close
                </Button>
              )}
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="text-sm text-red-600">❌ {error}</div>
              {error.includes("two-factor") && (
                <div className="text-xs text-red-500 mt-1">
                  Please complete 2FA on your device and try again
                </div>
              )}
              <Button variant="outline" onClick={() => setError(null)} className="mt-2 w-full">
                Try Again
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}