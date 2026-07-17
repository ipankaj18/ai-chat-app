interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function ChatInput({ value, onChange, onSubmit, disabled }: ChatInputProps) {
  return (
    <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            onSubmit();
          }
        }}
        placeholder="Type a message..."
        disabled={disabled}
        style={{ flex: 1, padding: '10px 12px', borderRadius: '8px', border: '1px solid #d1d5db' }}
      />
      <button onClick={onSubmit} disabled={disabled} style={{ padding: '10px 14px', borderRadius: '8px', border: 'none', backgroundColor: '#2563eb', color: '#fff' }}>
        Send
      </button>
    </div>
  );
}
