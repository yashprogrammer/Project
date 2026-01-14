import { ChatMessage } from "@/types/ChatMessage";
import { ChunkMetadata } from "@/types/Chunk";
import { parseBotJson, formatMessageTime, parseTextWithCitations } from "@/utils/chat";
import { Bot } from "lucide-react";
import { useMemo } from "react";
import BotJsonCard from "./BotJsonCard";

export default function BotMessageBubble({
  message,
  chunksMetadata,
}: {
  message: ChatMessage;
  chunksMetadata: { [key: string]: ChunkMetadata };
}) {
  const baseColor = "#3b82f6"; // Blue
  const bubbleBg = "rgba(59, 130, 246, 0.1)";
  const textColor = "#1f2937";
  const accentColor = baseColor;

  // Parse JSON only when the message is finalized (not streaming)
  const botJson = useMemo(() => {
    if (message.streaming) return null;
    return parseBotJson(message.content);
  }, [message.streaming, message.content]);

  return (
    <div className="flex items-start gap-2 sm:gap-3 justify-start animate-fadeIn">
      {/* Bot avatar */}
      <div
        className="mt-0.5 sm:mt-1 rounded-full p-1.5 sm:p-2 shadow-lg flex-shrink-0"
        style={{
          background: accentColor,
          color: "#ffffff",
        }}
        title="Bot"
      >
        <Bot className="h-3 w-3 sm:h-4 sm:w-4" />
      </div>
      
      {/* Bot bubble */}
      <div
        className="max-w-[85%] sm:max-w-[80%] rounded-xl sm:rounded-2xl rounded-tl-sm px-3 py-2 sm:px-4 sm:py-3 text-xs sm:text-sm shadow-md transition-all duration-200"
        style={{
          background: bubbleBg,
          color: textColor,
          borderLeftWidth: "3px",
          borderLeftStyle: "solid",
          borderLeftColor: accentColor,
          borderWidth: "1px",
          borderStyle: "solid",
          borderColor: `${accentColor}40`,
        }}
      >
        {botJson ? (
          <BotJsonCard data={botJson} chunksMetadata={chunksMetadata} />
        ) : (
          <>
            <pre className="whitespace-pre-wrap break-words font-sans leading-relaxed">
              {message.content}
            </pre>
            {message.streaming && (
              <span 
                className="inline-block w-1.5 sm:w-2 h-3 sm:h-4 align-baseline animate-pulse ml-1 sm:ml-1.5 rounded-sm"
                style={{ backgroundColor: `${accentColor}60` }}
              />
            )}
          </>
        )}
        {message.timestamp && !message.streaming && (
          <div className="mt-1.5 text-[10px] text-gray-500">
            {formatMessageTime(message.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}

