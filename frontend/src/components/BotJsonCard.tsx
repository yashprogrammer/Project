import { BotJson } from "@/types/BotJson";
import { ChunkMetadata } from "@/types/Chunk";
import { parseTextWithCitations } from "@/utils/chat";

export default function BotJsonCard({
  data,
  chunksMetadata,
}: {
  data: BotJson;
  chunksMetadata: { [key: string]: ChunkMetadata };
}) {
  return (
    <div className="space-y-3">
      {/* Sentiment & Intent */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-700 font-medium">
          {data.sentiment}
        </span>
        <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
          Intent: {data.intent}
        </span>
      </div>

      {/* Suggested Response */}
      <div>
        <div className="text-xs font-semibold text-gray-600 mb-1">Suggested Response:</div>
        <div className="text-sm text-gray-900 bg-white p-2 rounded border border-gray-200">
          {data.suggested_response}
        </div>
      </div>

      {/* Agent Guidance */}
      <div>
        <div className="text-xs font-semibold text-gray-600 mb-1">Agent Guidance:</div>
        <div className="text-sm text-gray-700 italic">
          {data.agent_guidance}
        </div>
      </div>

      {/* Facts with Citations */}
      {data.facts && data.facts.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-600 mb-1">Facts:</div>
          <ul className="space-y-1">
            {data.facts.map((fact, idx) => {
              const parts = parseTextWithCitations(fact, chunksMetadata);
              return (
                <li key={idx} className="text-sm text-gray-700 flex items-start gap-1">
                  <span className="text-gray-400 mt-1">•</span>
                  <span>
                    {parts.map((part, partIdx) => {
                      if (part.type === "citation") {
                        const metadata = part.chunkId ? chunksMetadata[part.chunkId] : null;
                        return (
                          <span
                            key={partIdx}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-xs rounded bg-blue-50 text-blue-700 border border-blue-200"
                            title={metadata ? `From: ${metadata.file_name}` : ""}
                          >
                            {part.content}
                          </span>
                        );
                      }
                      return <span key={partIdx}>{part.content}</span>;
                    })}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Sarcasm Detection */}
      {data.sarcasm?.detected && (
        <div className="p-2 rounded bg-yellow-50 border border-yellow-200">
          <div className="text-xs font-semibold text-yellow-800 mb-1">
            ⚠️ Sarcasm Detected ({(data.sarcasm.confidence * 100).toFixed(0)}%)
          </div>
          {data.sarcasm.reason && (
            <div className="text-xs text-yellow-700">{data.sarcasm.reason}</div>
          )}
          {data.sarcasm.type && (
            <div className="text-xs text-yellow-600 mt-1">
              Type: {data.sarcasm.type.replace("_", " ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

