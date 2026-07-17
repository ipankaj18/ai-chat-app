interface CacheBadgeProps {
  cached: boolean;
}

export function CacheBadge({ cached }: CacheBadgeProps) {
  if (!cached) return null;

  return <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>Cached response</div>;
}
