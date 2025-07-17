import React, { useState } from "react";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../ui/select";
import { Input } from "../ui/input";
import { Button } from "../ui/button";

const LMS_OPTIONS = [
  { label: "Brightspace", value: "brightspace" },
  { label: "Canvas", value: "canvas" },
  { label: "Moodle", value: "moodle" },
];

export default function LMSImportForm() {
  const [lmsType, setLmsType] = useState<string>(LMS_OPTIONS[0].value);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(null);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/import/lms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lms_type: lmsType,
          username,
          password,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Import failed. Please check your credentials.");
      } else {
        setSuccess(data.message || "Import successful!");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-md w-full mx-auto bg-white rounded-lg shadow p-6 space-y-6 border">
      <h2 className="text-xl font-semibold mb-2">Import from LMS</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">LMS Type</label>
          <Select value={lmsType} onValueChange={setLmsType}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select LMS" />
            </SelectTrigger>
            <SelectContent>
              {LMS_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Username</label>
          <Input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            placeholder="Enter your LMS username"
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <Input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            placeholder="Enter your LMS password"
            className="w-full"
          />
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Importing..." : "Import from LMS"}
        </Button>
        {success && <div className="text-green-600 text-sm mt-2">{success}</div>}
        {error && <div className="text-red-600 text-sm mt-2">{error}</div>}
      </div>
    </form>
  );
} 