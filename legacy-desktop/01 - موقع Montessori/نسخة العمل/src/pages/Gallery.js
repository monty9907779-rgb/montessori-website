import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getGalleryItems, updateGalleryItem } from '../utils/database';
import FlipBook from '../components/FlipBook';
import { Search, Calendar, Tags, ExternalLink, Edit3 } from 'lucide-react';

export default function Gallery() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [driveUrl, setDriveUrl] = useState('');
  const [, forceUpdate] = useState(0);

  const items = getGalleryItems();
  const isAdmin = user?.role === 'admin' || user?.role === 'director';

  const visible = items.filter(item => {
    const q = search.toLowerCase();
    return item.title.toLowerCase().includes(q) || item.description.toLowerCase().includes(q) || item.tags?.some(t => t.includes(q));
  });

  const handleSaveDrive = (id) => {
    updateGalleryItem(id, { driveLink: driveUrl });
    setEditingId(null);
    setDriveUrl('');
    forceUpdate(r => r + 1);
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 24, flexWrap: 'wrap' }}>
        <div className="search-bar">
          <Search size={15} />
          <input placeholder="Search gallery..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <span style={{ fontSize: '0.82rem', color: 'var(--text-light)' }}>{items.length} items</span>
      </div>

      {visible.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: '4rem', marginBottom: 12 }}>📸</div>
          <h3>No photos yet</h3>
          <p>Gallery photos will appear here once uploaded.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 20 }}>
          {visible.map((item) => (
            <div key={item.id} className="card" style={{ overflow: 'hidden' }}>
              <div style={{
                width: '100%', height: 200,
                background: 'var(--green-pale)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                overflow: 'hidden', position: 'relative',
              }}>
                <img
                  src={item.image}
                  alt={item.title}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.parentElement.textContent = '📷';
                  }}
                />
                {item.driveLink && (
                  <div style={{ position: 'absolute', bottom: 8, right: 8 }}>
                    <FlipBook driveLink={item.driveLink} title={item.title} />
                  </div>
                )}
              </div>
              <div className="card-body">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', color: 'var(--green-deep)', marginBottom: 6 }}>
                    {item.title}
                  </h3>
                  {isAdmin && (
                    <button className="btn btn-ghost btn-sm" onClick={() => {
                      setEditingId(item.id);
                      setDriveUrl(item.driveLink || '');
                    }}><Edit3 size={14} /></button>
                  )}
                </div>
                <p style={{ color: 'var(--text-mid)', fontSize: '0.85rem', marginBottom: 12, lineHeight: 1.5 }}>
                  {item.description}
                </p>

                {editingId === item.id && (
                  <div style={{ marginBottom: 12, padding: 12, background: 'var(--cream)', borderRadius: 8 }}>
                    <label className="form-label">Google Drive Link</label>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        className="form-input"
                        style={{ fontSize: '0.82rem' }}
                        placeholder="https://drive.google.com/file/d/... or /folders/..."
                        value={driveUrl}
                        onChange={e => setDriveUrl(e.target.value)}
                      />
                      <button className="btn btn-primary btn-sm" onClick={() => handleSaveDrive(item.id)}>Save</button>
                      <button className="btn btn-ghost btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', color: 'var(--text-light)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Calendar size={12} /> {item.date}
                  </span>
                  {item.tags && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Tags size={12} /> {item.tags.join(', ')}
                    </span>
                  )}
                </div>
                {item.driveLink && (
                  <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#4285F4', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <ExternalLink size={11} /> Drive folder attached
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}