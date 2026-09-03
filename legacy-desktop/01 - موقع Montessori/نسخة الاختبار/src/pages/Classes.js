import { useState } from 'react';
import { getClasses, getStudents, addClass, updateClass, deleteClass } from '../utils/database';
import { Plus, Edit2, Trash2, X, Users } from 'lucide-react';

const COLORS = ['#2d5016','#7ab648','#c4712a','#3b82f6','#8b5cf6','#f59e0b','#ec4899','#14b8a6'];
const EMPTY = { name: '', ageRange: '', monthlyFee: '', color: '#2d5016' };

export default function Classes() {
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [, forceUpdate] = useState(0);

  const classes = getClasses();
  const students = getStudents();

  const openAdd = () => { setForm(EMPTY); setEditId(null); setModal(true); };
  const openEdit = (c) => { setForm(c); setEditId(c.id); setModal(true); };
  const closeModal = () => { setModal(false); setEditId(null); };

  const save = () => {
    if (!form.name || !form.monthlyFee) return alert('Name and fee are required');
    if (editId) updateClass(editId, { ...form, monthlyFee: Number(form.monthlyFee) });
    else addClass({ ...form, monthlyFee: Number(form.monthlyFee) });
    closeModal();
    forceUpdate(r => r + 1);
  };

  const remove = (id) => {
    const count = students.filter(s => s.classId === id).length;
    if (count > 0) return alert(`Cannot delete: ${count} student(s) are in this class.`);
    if (window.confirm('Delete this class?')) { deleteClass(id); forceUpdate(r => r + 1); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn btn-primary" onClick={openAdd}><Plus size={15} /> Add Class</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {classes.map(cls => {
          const count = students.filter(s => s.classId === cls.id && s.status === 'active').length;
          return (
            <div key={cls.id} className="card" style={{ borderTop: `4px solid ${cls.color}` }}>
              <div className="card-body">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', color: 'var(--green-deep)' }}>{cls.name}</h3>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(cls)}><Edit2 size={13} /></button>
                    <button className="btn btn-danger btn-sm btn-icon" onClick={() => remove(cls.id)}><Trash2 size={13} /></button>
                  </div>
                </div>
                <div style={{ color: 'var(--text-light)', fontSize: '0.83rem', marginBottom: 14 }}>Ages: {cls.ageRange || 'Not set'}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-mid)', fontSize: '0.85rem' }}>
                    <Users size={14} />
                    <span>{count} student{count !== 1 ? 's' : ''}</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', color: cls.color, fontWeight: 700 }}>
                    SAR {Number(cls.monthlyFee).toLocaleString()}<span style={{ fontSize: '0.7rem', color: 'var(--text-light)', fontWeight: 400 }}>/mo</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{editId ? 'Edit Class' : 'Add New Class'}</span>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={16} /></button>
            </div>

            <div className="form-group">
              <label className="form-label">Class Name *</label>
              <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Primary" />
            </div>
            <div className="form-group">
              <label className="form-label">Age Range</label>
              <input className="form-input" value={form.ageRange} onChange={e => setForm({ ...form, ageRange: e.target.value })} placeholder="e.g. 3 – 6 years" />
            </div>
            <div className="form-group">
              <label className="form-label">Monthly Fee (SAR) *</label>
              <input className="form-input" type="number" value={form.monthlyFee} onChange={e => setForm({ ...form, monthlyFee: e.target.value })} placeholder="1500" />
            </div>
            <div className="form-group">
              <label className="form-label">Color</label>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 4 }}>
                {COLORS.map(c => (
                  <button key={c} onClick={() => setForm({ ...form, color: c })}
                    style={{ width: 32, height: 32, borderRadius: '50%', background: c, border: form.color === c ? '3px solid var(--text-dark)' : '2px solid transparent', cursor: 'pointer', outline: 'none' }} />
                ))}
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={closeModal}>Cancel</button>
              <button className="btn btn-primary" onClick={save}>{editId ? 'Save Changes' : 'Add Class'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
