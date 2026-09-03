import { useState } from 'react';
import { getTeachers, getClasses, addTeacher, updateTeacher, deleteTeacher } from '../utils/database';
import { Plus, Edit2, Trash2, X, Mail, Phone } from 'lucide-react';

const EMPTY = { name: '', email: '', phone: '', specialization: '', classId: '', status: 'active', joinDate: new Date().toISOString().slice(0, 10) };

export default function Teachers() {
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [refresh, setRefresh] = useState(0);

  const teachers = getTeachers();
  const classes = getClasses();

  const visible = teachers.filter(t => {
    const q = search.toLowerCase();
    return t.name.toLowerCase().includes(q) || t.specialization?.toLowerCase().includes(q) || t.email?.toLowerCase().includes(q);
  });

  const openAdd = () => { setForm(EMPTY); setEditId(null); setModal('add'); };
  const openEdit = (t) => { setForm(t); setEditId(t.id); setModal('edit'); };
  const closeModal = () => { setModal(null); setEditId(null); };

  const save = () => {
    if (!form.name || !form.email) return alert('Name and email are required');
    if (editId) updateTeacher(editId, form);
    else addTeacher(form);
    closeModal();
    setRefresh(r => r + 1);
  };

  const remove = (id) => {
    if (window.confirm('Remove this teacher?')) {
      deleteTeacher(id);
      setRefresh(r => r + 1);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="search-bar">
          <input placeholder="Search teachers…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={openAdd} style={{ marginLeft: 'auto' }}>
          <Plus size={15} /> Add Teacher
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Specialization</th>
                <th>Assigned Class</th>
                <th>Joined</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-light)' }}>No teachers found</td></tr>
              )}
              {visible.map(t => {
                const cls = classes.find(c => c.id === t.classId);
                return (
                  <tr key={t.id}>
                    <td><strong>{t.name}</strong></td>
                    <td><a href={`mailto:${t.email}`} style={{ color: 'var(--green-mid)', textDecoration: 'none' }}><Mail size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />{t.email}</a></td>
                    <td>{t.phone && <a href={`tel:${t.phone}`} style={{ color: 'var(--text-mid)', textDecoration: 'none' }}><Phone size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />{t.phone}</a>}</td>
                    <td><span className="badge badge-blue">{t.specialization || '—'}</span></td>
                    <td>
                      {cls
                        ? <span style={{ background: cls.color + '22', color: cls.color, padding: '3px 10px', borderRadius: 20, fontSize: '0.78rem', fontWeight: 600 }}>{cls.name}</span>
                        : <span style={{ color: 'var(--text-light)' }}>Unassigned</span>}
                    </td>
                    <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{t.joinDate}</td>
                    <td>
                      <span className={`badge ${t.status === 'active' ? 'badge-success' : 'badge-warning'}`}>{t.status}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(t)}><Edit2 size={13} /></button>
                        <button className="btn btn-danger btn-sm btn-icon" onClick={() => remove(t.id)}><Trash2 size={13} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{editId ? 'Edit Teacher' : 'Add New Teacher'}</span>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={16} /></button>
            </div>

            <div className="form-group">
              <label className="form-label">Full Name *</label>
              <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Noura Al-Saud" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Email *</label>
                <input className="form-input" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="teacher@montessori.com" />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+966…" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Specialization</label>
              <input className="form-input" value={form.specialization} onChange={e => setForm({ ...form, specialization: e.target.value })} placeholder="e.g. Montessori Primary" />
            </div>
            <div className="form-group">
              <label className="form-label">Assigned Class</label>
              <select className="form-select" value={form.classId} onChange={e => setForm({ ...form, classId: e.target.value })}>
                <option value="">Unassigned</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Join Date</label>
                <input className="form-input" type="date" value={form.joinDate} onChange={e => setForm({ ...form, joinDate: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Status</label>
                <select className="form-select" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={closeModal}>Cancel</button>
              <button className="btn btn-primary" onClick={save}>{editId ? 'Save Changes' : 'Add Teacher'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
