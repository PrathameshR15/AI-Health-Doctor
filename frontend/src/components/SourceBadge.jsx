import React from 'react';
import { ExternalLink, BookOpen } from 'lucide-react';

export default function SourceBadge({ source }) {
  if (!source) return null;

  const orgColors = {
    WHO: { bg: '#e0f2fe', text: '#0369a1', border: '#bae6fd' },
    NHS: { bg: '#ede9fe', text: '#5b21b6', border: '#ddd6fe' },
    MedlinePlus: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' },
    ICMR: { bg: '#dcfce7', text: '#166534', border: '#bbf7d0' },
    'NCDC India': { bg: '#ffedd5', text: '#9a3412', border: '#fed7aa' },
  };

  const style = orgColors[source.organization] || { bg: '#f1f5f9', text: '#334155', border: '#cbd5e1' };

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="badge badge-source"
      style={{
        backgroundColor: style.bg,
        color: style.text,
        borderColor: style.border,
        padding: '0.35rem 0.65rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4rem',
        borderRadius: '8px',
        fontSize: '0.78rem',
        fontWeight: '600',
        textDecoration: 'none',
        margin: '0.2rem'
      }}
      title={`Open official guideline: ${source.title}`}
    >
      <BookOpen size={13} />
      <span><strong>{source.organization}:</strong> {source.title ? source.title.slice(0, 40) + '...' : 'Clinical Reference'}</span>
      <ExternalLink size={12} style={{ opacity: 0.7 }} />
    </a>
  );
}
