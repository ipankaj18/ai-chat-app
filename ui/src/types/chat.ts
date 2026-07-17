export interface Message {
  role: 'user' | 'assistant';
  content: string;
  cached?: boolean;
}

export interface ChatRequest {
  message: string;
  history: Message[];
}

export interface ChatResponse {
  reply: string;
  cached: boolean;
}
