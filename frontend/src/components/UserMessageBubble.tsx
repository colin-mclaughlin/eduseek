import React from "react";
import { cn } from "@/lib/utils";

interface UserMessageBubbleProps {
  content: string;
  timestamp: string;
}

const UserMessageBubble: React.FC<UserMessageBubbleProps> = ({ content, timestamp }) => (
  <div className={cn(
    "flex justify-end mb-2"
  )}>
    <div className="max-w-[75%] bg-primary text-primary-foreground rounded-lg rounded-br-none px-4 py-2 shadow-sm">
      <div className="text-sm whitespace-pre-line">{content}</div>
      <div className="text-xs text-muted-foreground mt-1 text-right">{timestamp}</div>
    </div>
  </div>
);

export default UserMessageBubble; 