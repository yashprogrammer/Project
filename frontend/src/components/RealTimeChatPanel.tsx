import { useState, useEffect, useRef } from "react";
import {
  usePipecatClient,
  usePipecatClientTransportState,
  useRTVIClientEvent,
  PipecatClientMicToggle,
  PipecatClientAudio,
} from "@pipecat-ai/client-react";
import { RTVIEvent, TransportStateEnum } from "@pipecat-ai/client-js";
import { Play, StopCircle, Mic, MicOff, Send, Bot, ChevronDown } from "lucide-react";
import { ChatMessage } from "@/types/ChatMessage";
import { ChunkMetadata } from "@/types/Chunk";
import { getId } from "@/utils/chat";
import BotMessageBubble from "./BotMessageBubble";
import UserMessageBubble from "./UserMessageBubble";
import usePipecatChatEvents from "@/hooks/pipecat-chat-events";
import api from "@/lib/api";

interface RealTimeChatPanelProps {
  departmentId?: string;
  onDepartmentChange?: (id: string) => void;
}

export default function RealTimeChatPanel({
  departmentId,
  onDepartmentChange
}: RealTimeChatPanelProps) {
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();

  const [text, setText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chunksMetadata, setChunksMetadata] = useState<{ [key: string]: ChunkMetadata }>({});
  const [departments, setDepartments] = useState<any[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<string>(departmentId || "");

  const listRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Subscribe to Pipecat chat events
  usePipecatChatEvents(setMessages, setChunksMetadata);

  // Load departments on mount
  useEffect(() => {
    const loadDepartments = async () => {
      try {
        const response = await api.get("/departments");
        setDepartments(response.data);
        if (response.data.length > 0 && !selectedDeptId) {
          const firstDept = response.data[0];
          setSelectedDeptId(firstDept._id);
          onDepartmentChange?.(firstDept._id);
        }
      } catch (error) {
        console.error("Failed to load departments:", error);
      }
    };
    loadDepartments();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const isConnecting =
    transportState === TransportStateEnum.CONNECTING || transportState === TransportStateEnum.AUTHENTICATING;
  const isConnected = transportState === TransportStateEnum.READY;

  useRTVIClientEvent(RTVIEvent.BotReady, () => {
    console.log("Bot is ready");
  });

  useRTVIClientEvent(RTVIEvent.Error, (error: any) => {
    console.error("Connection error:", error);
  });

  const handleConnect = async () => {
    const deptId = selectedDeptId || departmentId;
    if (!deptId) {
      alert("Please select a department");
      return;
    }

    const endpoint = import.meta.env.VITE_PIPECAT_ENDPOINT || "/stream/connect";
    
    try {
      const response = await api.post(endpoint, {
        department_id: deptId
      });

      await client.connect(response.data.ws_url);
    } catch (error: any) {
      console.error("Failed to connect:", error);
      alert(`Connection Error: ${error?.message || "Unknown error"}`);
    }
  };

  const handleDisconnect = async () => {
    try {
      if (transportState === TransportStateEnum.DISCONNECTED || transportState === TransportStateEnum.DISCONNECTING) return;
      await client?.disconnect();
    } catch (error: any) {
      if (
        error?.message?.includes("Session ended") ||
        error?.toString().includes("Session ended")
      ) {
        console.log("Session already ended");
        return;
      }
      console.error("Failed to disconnect:", error);
    }
  };

  const handleSendText = async () => {
    const payload = text.trim();
    if (!payload || !client) return;

    await client.sendText(payload);

    setMessages((prev) => [
      ...prev,
      { id: getId(), role: "user", content: payload, timestamp: new Date() },
    ]);
    setText("");
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg border bg-blue-50 border-blue-200">
            <Bot className="h-4 w-4 text-blue-600" />
          </div>
          <div className="flex flex-col gap-1">
            <h3 className="text-lg font-semibold text-gray-900">Real-time Chat</h3>
            <p className="text-xs text-gray-600">Live conversation</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Department Selector */}
          <select
            value={selectedDeptId}
            onChange={(e) => {
              setSelectedDeptId(e.target.value);
              onDepartmentChange?.(e.target.value);
            }}
            disabled={isConnected}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white disabled:opacity-50"
          >
            <option value="">Select Department</option>
            {departments.map((dept) => (
              <option key={dept._id} value={dept._id}>
                {dept.name}
              </option>
            ))}
          </select>

          {/* Mic Toggle */}
          <PipecatClientMicToggle disabled={!isConnected}>
            {({ disabled, isMicEnabled, onClick }) => (
              <button
                disabled={disabled}
                onClick={onClick}
                className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${
                  isMicEnabled
                    ? "text-green-700 border-green-500 bg-green-50"
                    : "text-red-700 border-red-500 bg-red-50"
                } ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                {isMicEnabled ? <Mic className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
              </button>
            )}
          </PipecatClientMicToggle>

          {/* Start/Stop Button */}
          <button
            onClick={isConnected ? handleDisconnect : handleConnect}
            disabled={isConnecting || !selectedDeptId}
            className={`px-3 py-1.5 text-xs font-medium text-white rounded-lg transition-all disabled:opacity-40 ${
              isConnected ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {isConnected ? (
              <>
                <StopCircle className="h-3.5 w-3.5 inline mr-1" />
                Stop
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 inline mr-1" />
                {isConnecting ? "Connecting" : "Start"}
              </>
            )}
          </button>

          {/* Status Badge */}
          <div className={`px-2.5 py-1 text-xs rounded-lg ${
            isConnecting
              ? "bg-yellow-100 text-yellow-700"
              : isConnected
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-700"
          }`}>
            <div className="flex items-center gap-1.5">
              <div className={`h-1.5 w-1.5 rounded-full ${
                isConnecting
                  ? "bg-yellow-600 animate-pulse"
                  : isConnected
                    ? "bg-green-600 animate-pulse"
                    : "bg-gray-400"
              }`} />
              <span>
                {isConnecting ? "Connecting..." : isConnected ? "Connected" : "Idle"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden audio element */}
      <div className="hidden">
        <PipecatClientAudio />
      </div>

      {/* Chat Messages */}
      <div
        ref={listRef}
        className="flex-1 min-h-0 overflow-y-auto space-y-3 p-4 bg-white"
      >
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center space-y-2">
              <div className="inline-flex p-4 rounded-full border border-gray-200 bg-blue-50">
                <Bot className="h-8 w-8 text-blue-600" />
              </div>
              <p className="text-sm text-gray-600 font-medium">No messages yet</p>
              <p className="text-xs text-gray-500">Speak or type to start a conversation</p>
            </div>
          </div>
        ) : (
          messages.map((m) => {
            if (m.role === "bot") {
              return (
                <BotMessageBubble
                  key={m.id}
                  message={m}
                  chunksMetadata={chunksMetadata}
                />
              );
            }
            return <UserMessageBubble key={m.id} message={m} />;
          })
        )}
        <div ref={endRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t border-gray-200 bg-white p-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={isConnected ? "Type a message..." : "Connect to send messages"}
            disabled={!isConnected}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white disabled:opacity-50"
            onKeyDown={(e) => {
              if (e.key === "Enter" && isConnected && text.trim()) {
                handleSendText();
              }
            }}
          />
          <button
            onClick={handleSendText}
            disabled={!text.trim() || !isConnected}
            className="px-3 py-2 rounded-lg text-white bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

