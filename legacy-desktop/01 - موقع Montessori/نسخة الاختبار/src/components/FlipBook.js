import { useState } from 'react';
import { ExternalLink, X } from 'lucide-react';

export default function FlipBook({ driveLink, title }) {
  const [open, setOpen] = useState(false);

  const getEmbedUrl = (url) => {
    if (!url) return null;
    const fileMatch = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
    if (fileMatch) return `https://drive.google.com/file/d/${fileMatch[1]}/preview`;
    const folderMatch = url.match(/\/folders\/([a-zA-Z0-9_-]+)/);
    if (folderMatch) return `https://drive.google.com/embeddedfolderview?id=${folderMatch[1]}`;
    const idMatch = url.match(/id=([a-zA-Z0-9_-]+)/);
    if (idMatch) return `https://drive.google.com/embeddedfolderview?id=${idMatch[1]}`;
    if (url.includes('drive.google.com')) return url;
    return null;
  };

  const embedUrl = getEmbedUrl(driveLink);
  if (!embedUrl) return null;

  return (
    <>
      <button
        className="btn btn-sm"
        style={{ background: '#4285F4', color: '#fff', fontSize: '0.78rem' }}
        onClick={() => setOpen(true)}
      >
        <ExternalLink size={13} /> View Flip Book
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" style={{ maxWidth: 900, padding: 16 }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ fontFamily: 'var(--font-display)', color: 'var(--green-deep)', fontSize: '1.05rem' }}>{title}</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}><X size={18} /></button>
            </div>
            <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden', borderRadius: 8 }}>
              <iframe
                src={embedUrl}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                allow="autoplay"
                title={title}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}