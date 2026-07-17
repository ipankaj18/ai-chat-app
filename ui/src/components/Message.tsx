import type { Message as MessageType } from '../types/chat';

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: '12px' }}>
      <div
        style={{
          maxWidth: '70%',
          padding: '10px 14px',
          borderRadius: '12px',
          backgroundColor: isUser ? '#2563eb' : '#f3f4f6',
          color: isUser ? '#fff' : '#111827',
          whiteSpace: 'pre-wrap',
        }}
      >
        {message.content}
      </div>
    </div>
  );
}
