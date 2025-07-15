import React, { useState } from "react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  loading?: boolean;
}

export const QuestionInput: React.FC<QuestionInputProps> = ({ onSubmit, loading }) => {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value.trim());
      setValue("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 w-full mt-8">
      <Input
        type="text"
        placeholder="Ask a question about your files..."
        value={value}
        onChange={e => setValue(e.target.value)}
        className="flex-1"
        disabled={loading}
        maxLength={200}
        autoFocus
      />
      <Button type="submit" disabled={loading || !value.trim()}>
        Ask
      </Button>
    </form>
  );
};

export default QuestionInput; 