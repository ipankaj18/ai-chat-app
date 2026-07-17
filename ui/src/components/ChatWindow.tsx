import { useState } from 'react';
import { ChatInput } from './ChatInput';
import { Message } from './Message';
import { CacheBadge } from './CacheBadge';
import { sendMessage } from '../services/api';
import type { Message as MessageType } from '../types/chat';

export function ChatWindow() {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!input.trim() || loading) return;

    const userMessage: MessageType = { role: 'user', content: input.trim() };
    const history = [...messages, userMessage];
    setMessages(history);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage({ message: userMessage.content, history });
      const assistantMessage: MessageType = { role: 'assistant', content: response.reply, cached: response.cached };
      setMessages([...history, assistantMessage]);
    } catch (error) {
      setMessages([...history, { role: 'assistant', content: 'Unable to reach the server.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '720px', margin: '40px auto', padding: '24px', border: '1px solid #e5e7eb', borderRadius: '16px', boxShadow: '0 8px 24px rgba(0,0,0,0.08)' }}>
      <h1 style={{ marginBottom: '16px' }}>AI Chat App</h1>
      <div style={{ minHeight: '360px', backgroundColor: '#fafafa', padding: '16px', borderRadius: '12px', overflowY: 'auto' }}>
        {messages.length === 0 && <p style={{ color: '#6b7280' }}>Start a conversation...</p>}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`}>
            <Message message={message} />
            {message.role === 'assistant' &&
              index === messages.length - 1 && (
              <CacheBadge cached={message.cached ?? false} />
            )}
          </div>
        ))}
      </div>
      <ChatInput value={input} onChange={setInput} onSubmit={handleSubmit} disabled={loading} />
    </div>
  );
}
