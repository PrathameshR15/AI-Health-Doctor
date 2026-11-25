import React, { useState } from 'react';
import { Activity, Stethoscope, FileText, Pill, Calendar, Info } from 'lucide-react';

export default function HealthTimelinePlot({ events = [] }) {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [filterType, setFilterType] = useState('all');

  if (!events || events.length === 0) {
    return (
      <div style={{
        padding: '2.5rem 1rem',
        textAlign: 'center',
        background: '#f8fafc',
        borderRadius: '12px',
        border: '1px dashed var(--border)',
        color: 'var(--text-muted)'
      }}>
        <Activity size={32} style={{ opacity: 0.35, marginBottom: '0.5rem' }} />
        <p style={{ margin: 0, fontWeight: '600' }}>No timeline events recorded yet to plot on the graph.</p>
        <p style={{ fontSize: '0.82rem', marginTop: '0.25rem' }}>
          When AI assessments are made, reports uploaded, or treatments prescribed, they appear on this interactive time-axis plot.
        </p>
      </div>
    );
  }

  // Filter events if requested
  const filteredEvents = events.filter(e => {
    if (filterType === 'all') return true;
    if (filterType === 'assessment') return e.event_label?.includes('Assessment');
    if (filterType === 'report') return e.event_label?.includes('Report');
    if (filterType === 'treatment') return e.event_label?.includes('Treatment') || e.event_label?.includes('Plan');
    return true;
  });

  // Sort events chronologically (oldest to newest for left-to-right plotting)
  const sortedEvents = [...filteredEvents].sort((a, b) => new Date(a.date) - new Date(b.date));

  // Determine lane / severity score for vertical Y-axis
  // Lanes:
  // Lane 3: Treatment / Approved Care (High positive action)
  // Lane 2: AI Assessments (Consultation)
  // Lane 1: Lab & Medical Reports (Diagnostics)
  const getEventMeta = (ev) => {
    const isTreatment = ev.event_label?.includes('Treatment') || ev.event_label?.includes('Plan');
    const isReport = ev.event_label?.includes('Report');
    const isAssessment = ev.event_label?.includes('Assessment');

    if (isTreatment) {
      return {
        lane: 3,
        color: '#16a34a',
        bg: '#dcfce7',
        border: '#15803d',
        icon: '💊',
        label: 'Treatment Started'
      };
    }
    if (isReport) {
      return {
        lane: 1,
        color: '#0d9488',
        bg: '#ccfbf1',
        border: '#0f766e',
        icon: '🔬',
        label: 'Report Analyzed'
      };
    }
    return {
      lane: 2,
      color: '#7c3aed',
      bg: '#ede9fe',
      border: '#6d28d9',
      icon: '🎯',
      label: 'AI Assessment Done'
    };
  };

  // Dimensions for SVG graph
  const width = 840;
  const height = 260;
  const padLeft = 80;
  const padRight = 50;
  const padTop = 35;
  const padBottom = 50;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const yLanes = [
    { lane: 3, label: '💊 Treatment', y: padTop + plotHeight * 0.15 },
    { lane: 2, label: '🎯 Assessment', y: padTop + plotHeight * 0.50 },
    { lane: 1, label: '🔬 Lab Report', y: padTop + plotHeight * 0.85 }
  ];

  const minTime = sortedEvents.length > 0 ? new Date(sortedEvents[0].date).getTime() : 0;
  const maxTime = sortedEvents.length > 0 ? new Date(sortedEvents[sortedEvents.length - 1].date).getTime() : 1;
  const timeSpan = maxTime - minTime || 1;

  // Calculate coordinates for each point
  const points = sortedEvents.map((ev, idx) => {
    const meta = getEventMeta(ev);
    const time = new Date(ev.date).getTime();
    
    // Spread evenly if single point or clustered closely
    let x;
    if (sortedEvents.length === 1) {
      x = padLeft + plotWidth / 2;
    } else {
      const timeRatio = (time - minTime) / timeSpan;
      // Add slight index-based distribution so points on same minute don't overlap completely
      const indexRatio = idx / (sortedEvents.length - 1);
      const blendedRatio = (timeRatio * 0.7) + (indexRatio * 0.3);
      x = padLeft + blendedRatio * plotWidth;
    }

    const laneObj = yLanes.find(l => l.lane === meta.lane) || yLanes[1];
    const y = laneObj.y;

    return {
      ...ev,
      meta,
      x,
      y
    };
  });

  // Generate SVG path connecting points sequentially
  const linePath = points.length > 1
    ? points.reduce((acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`, '')
    : '';

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      padding: '1.25rem',
      marginBottom: '1.5rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
    }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '800', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--dark)' }}>
            <Activity size={18} color="var(--primary)" /> Interactive Health Timeline Plot
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.2rem 0 0 0' }}>
            Visual progression over time: click any node on the graph to inspect clinical highlights.
          </p>
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '0.35rem', background: '#f1f5f9', padding: '0.25rem', borderRadius: '8px' }}>
          {[
            { id: 'all', label: `All (${events.length})` },
            { id: 'treatment', label: '💊 Treatment' },
            { id: 'assessment', label: '🎯 Assessments' },
            { id: 'report', label: '🔬 Reports' },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => { setFilterType(f.id); setSelectedEvent(null); }}
              style={{
                fontSize: '0.78rem',
                fontWeight: '700',
                padding: '0.25rem 0.65rem',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                background: filterType === f.id ? '#ffffff' : 'transparent',
                color: filterType === f.id ? 'var(--primary)' : 'var(--text-muted)',
                boxShadow: filterType === f.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Canvas Container */}
      <div style={{ width: '100%', overflowX: 'auto', background: 'linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '0.5rem 0' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', minWidth: '680px', height: 'auto', display: 'block' }}
        >
          <defs>
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
              <stop offset="50%" stopColor="#0284c7" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#16a34a" stopOpacity="0.8" />
            </linearGradient>
            <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.15" />
            </filter>
          </defs>

          {/* Lane Horizontal Background Guides */}
          {yLanes.map((lane) => (
            <g key={lane.lane}>
              <line
                x1={padLeft}
                y1={lane.y}
                x2={width - padRight}
                y2={lane.y}
                stroke="#e2e8f0"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <text
                x={padLeft - 12}
                y={lane.y + 4}
                textAnchor="end"
                fontSize="11"
                fontWeight="700"
                fill="#64748b"
              >
                {lane.label}
              </text>
            </g>
          ))}

          {/* Time Axis Base Line */}
          <line
            x1={padLeft}
            y1={height - padBottom + 12}
            x2={width - padRight}
            y2={height - padBottom + 12}
            stroke="#94a3b8"
            strokeWidth="1.5"
          />

          {/* Start and End Time Labels */}
          {sortedEvents.length > 0 && (
            <>
              <text
                x={padLeft}
                y={height - padBottom + 30}
                textAnchor="start"
                fontSize="10"
                fontWeight="600"
                fill="#64748b"
              >
                Start: {sortedEvents[0].date_time?.split('•')[0] || 'Start'}
              </text>
              <text
                x={width - padRight}
                y={height - padBottom + 30}
                textAnchor="end"
                fontSize="10"
                fontWeight="600"
                fill="#64748b"
              >
                Latest: {sortedEvents[sortedEvents.length - 1].date_time?.split('•')[0] || 'Present'}
              </text>
            </>
          )}

          {/* Connecting Path Between Chronological Events */}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke="url(#lineGrad)"
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}

          {/* Event Nodes */}
          {points.map((pt, idx) => {
            const isSelected = selectedEvent?.id === pt.id;
            return (
              <g
                key={pt.id || idx}
                onClick={() => setSelectedEvent(isSelected ? null : pt)}
                style={{ cursor: 'pointer' }}
              >
                {/* Outer halo when selected or hovered */}
                {isSelected && (
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r="16"
                    fill={pt.meta.bg}
                    stroke={pt.meta.border}
                    strokeWidth="2"
                    opacity="0.8"
                  />
                )}

                {/* Main Node Circle */}
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isSelected ? "9" : "7.5"}
                  fill={pt.meta.color}
                  stroke="#ffffff"
                  strokeWidth="2.5"
                  filter="url(#nodeShadow)"
                />

                {/* Node Top Highlight Callout (2 words or 3 words) */}
                <g transform={`translate(${pt.x}, ${pt.y - 14})`}>
                  <rect
                    x="-45"
                    y="-15"
                    width="90"
                    height="16"
                    rx="8"
                    fill={pt.meta.bg}
                    stroke={pt.meta.border}
                    strokeWidth="0.8"
                  />
                  <text
                    x="0"
                    y="-4"
                    textAnchor="middle"
                    fontSize="8.5"
                    fontWeight="800"
                    fill={pt.meta.color}
                  >
                    {pt.highlight ? (pt.highlight.length > 18 ? pt.highlight.substring(0, 16) + '..' : pt.highlight) : pt.meta.label}
                  </text>
                </g>

                {/* Node Date Tick at bottom */}
                <text
                  x={pt.x}
                  y={height - padBottom + 26}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#94a3b8"
                  fontWeight="600"
                >
                  {new Date(pt.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedEvent && (
        <div style={{
          marginTop: '1rem',
          padding: '1rem 1.25rem',
          background: selectedEvent.meta.bg,
          border: `1.5px solid ${selectedEvent.meta.border}`,
          borderRadius: '10px',
          animation: 'fadeIn 0.2s ease-in'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>{selectedEvent.meta.icon}</span>
              <div>
                <strong style={{ fontSize: '0.98rem', color: 'var(--dark)' }}>
                  {selectedEvent.event_label}
                </strong>
                <span style={{
                  marginLeft: '0.6rem',
                  fontSize: '0.82rem',
                  fontWeight: '800',
                  color: selectedEvent.meta.color,
                  background: '#ffffff',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '12px',
                  border: `1px solid ${selectedEvent.meta.border}40`
                }}>
                  {selectedEvent.highlight}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: '600' }}>
                📅 {selectedEvent.date_time}
              </span>
              <button
                onClick={() => setSelectedEvent(null)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontWeight: '700',
                  color: '#64748b',
                  fontSize: '0.88rem'
                }}
              >
                ✕
              </button>
            </div>
          </div>

          <p style={{ fontSize: '0.86rem', color: '#334155', margin: '0.5rem 0 0 0', lineHeight: '1.45' }}>
            {selectedEvent.summary}
          </p>

          {selectedEvent.details && (
            <div style={{
              marginTop: '0.4rem',
              fontSize: '0.8rem',
              color: '#475569',
              background: '#ffffff',
              padding: '0.45rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid rgba(0,0,0,0.06)'
            }}>
              {selectedEvent.details}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
