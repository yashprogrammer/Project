import { ChatMessage } from "@/types/ChatMessage";
import { formatMessageTime } from "@/utils/chat";
import { User } from "lucide-react";

export default function UserMessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex items-start gap-2 sm:gap-3 justify-end animate-fadeIn">
      {/* User bubble */}
      <div
        className="max-w-[85%] sm:max-w-[80%] rounded-xl sm:rounded-2xl rounded-tr-sm px-3 py-2 sm:px-4 sm:py-3 text-xs sm:text-sm shadow-md"
        style={{
          background: "#3b82f6",
          color: "#ffffff",
        }}
      >
        <pre className="whitespace-pre-wrap break-words font-sans leading-relaxed text-white">
          {message.content}
        </pre>
        {message.timestamp && !message.streaming && (
          <div className="mt-1.5 text-[10px] text-blue-100">
            {formatMessageTime(message.timestamp)}
          </div>
        )}
      </div>
      
      {/* User avatar */}
      <div
        className="mt-0.5 sm:mt-1 rounded-full p-1.5 sm:p-2 shadow-lg flex-shrink-0"
        style={{
          background: "#6b7280",
          color: "#ffffff",
        }}
        title="User"
      >
        <User className="h-3 w-3 sm:h-4 sm:w-4" />
      </div>
    </div>
  );
}

