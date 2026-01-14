import { PipecatClient } from '@pipecat-ai/client-js';
import { PipecatClientProvider, usePipecatClientTransportState } from '@pipecat-ai/client-react';
import { WebSocketTransport } from '@pipecat-ai/websocket-transport';
import { useState, useEffect } from 'react';
import RealTimeChatPanel from '@/components/RealTimeChatPanel';
import { TransportStateEnum } from "@pipecat-ai/client-js";

const Stream = () => {
  const [departmentId, setDepartmentId] = useState<string | undefined>(undefined);
  const transportState = usePipecatClientTransportState();
  const [client] = useState(() => {
    const transport = new WebSocketTransport();
    return new PipecatClient({ transport, enableMic: false });
  });

  useEffect(() => {
    return () => {
      if(transportState === TransportStateEnum.CONNECTED) {
        client?.disconnect();
      }
    };
  }, [client, transportState]);

  return (
    <PipecatClientProvider client={client}>
      <div className="h-full w-full bg-white">
        <RealTimeChatPanel
          departmentId={departmentId}
          onDepartmentChange={setDepartmentId}
        />
      </div>
    </PipecatClientProvider>
  );
};

export default Stream;

