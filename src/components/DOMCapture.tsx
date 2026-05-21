'use client';
import { useState, useEffect, useCallback } from 'react';
import { sendToSidecar } from '../lib/sidecar';

const PPM_STATUS_URL = 'http://localhost:7834/status';

export default function DOMCapture() {
  const [open, setOpen] = useState(false);
  const [serverOk, setServerOk] = useState<boolean | null>(null);
  const [sessionId, setSessionId] = useState('');
  const [script, setScript] = useState('');
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const checkServer = useCallback(() => {
    fetch(PPM_STATUS_URL, { signal: AbortSignal.timeout(2000) })
      .then(r => r.ok ? setServerOk(true) : setServerOk(false))
      .catch(() => setServerOk(false));
  }, []);

  useEffect(() => {
    if (open) checkServer();
  }, [open, checkServer]);

  async function handleGenerate() {
    setGenerating(true);
    setScript('');
    try {
      const res = await sendToSidecar({ type: 'generate_dom_playwright', session_id: sessionId }) as Record<string, unknown> | null;
      if (res?.type === 'dom_playwright_script') setScript((res.script as string) ?? '');
    } finally {
      setGenerating(false);
    }
  }

  async function handleDownloadExtension() {
    setDownloading(true);
    try {
      const res = await sendToSidecar({ type: 'get_extension_zip' }) as Record<string, unknown> | null;
      if (res?.type === 'extension_zip' && res.data) {
        const bytes = Uint8Array.from(atob(res.data as string), c => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: 'application/zip' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ppm-chrome-extension.zip';
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div style={{ background: '#1e293b', borderRadius: 10, marginBottom: 18, overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', background: 'none', border: 'none', color: '#f8fafc',
          padding: '12px 16px', textAlign: 'left', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 14,
        }}
      >
        <span style={{ fontWeight: 600 }}>🌐 DOM Capture (Chrome Extension)</span>
        <span style={{ color: '#64748b', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ padding: '0 16px 16px' }}>
          {/* Server status */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
            padding: '8px 12px', background: '#0f172a', borderRadius: 6, fontSize: 12,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
              background: serverOk === null ? '#64748b' : serverOk ? '#22c55e' : '#ef4444',
            }} />
            <span style={{ color: '#94a3b8' }}>
              {serverOk === null ? 'Checking server…' : serverOk ? 'PPM server running on port 7834' : 'Server not reachable — start the sidecar first'}
            </span>
            <button
              onClick={checkServer}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', fontSize: 11 }}
            >
              Refresh
            </button>
          </div>

          {/* Instructions */}
          <p style={{ color: '#94a3b8', fontSize: 12, margin: '0 0 10px', lineHeight: 1.5 }}>
            1. Download the extension and load it unpacked in Chrome (<code>chrome://extensions</code> → Developer mode → Load unpacked).<br />
            2. Click <strong>Start Recording</strong> in the extension popup, perform your workflow, then click <strong>Send to PPM</strong>.<br />
            3. Enter an optional session ID below and click <strong>Generate Script</strong>.
          </p>

          {/* Download extension */}
          <button
            onClick={handleDownloadExtension}
            disabled={downloading}
            style={{
              padding: '7px 14px', background: '#3b82f6', border: 'none', borderRadius: 6,
              color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer', marginBottom: 12,
            }}
          >
            {downloading ? 'Packaging…' : '📦 Download Extension (.zip)'}
          </button>

          {/* Session ID input */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input
              value={sessionId}
              onChange={e => setSessionId(e.target.value)}
              placeholder="Session ID (leave blank for latest)"
              style={{
                flex: 1, background: '#0f172a', border: '1px solid #334155', borderRadius: 6,
                color: '#f8fafc', padding: '7px 10px', fontSize: 12,
              }}
            />
            <button
              onClick={handleGenerate}
              disabled={generating || !serverOk}
              style={{
                padding: '7px 14px', background: '#10b981', border: 'none', borderRadius: 6,
                color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                opacity: (!serverOk || generating) ? 0.5 : 1,
              }}
            >
              {generating ? 'Generating…' : '⚡ Generate Script'}
            </button>
          </div>

          {/* Script output */}
          {script && (
            <pre style={{
              background: '#0f172a', borderRadius: 6, padding: 12, fontSize: 11,
              color: '#a5f3fc', overflowX: 'auto', maxHeight: 300, margin: 0,
              whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            }}>
              {script}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
