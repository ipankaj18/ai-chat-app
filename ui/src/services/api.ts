import type { ChatRequest, ChatResponse } from '../types/chat';

export async function sendMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to send message');
  }

  return response.json();
}
