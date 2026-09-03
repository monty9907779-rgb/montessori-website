import { useState } from 'react';
import { getStudents, getClasses, addStudent, updateStudent, deleteStudent, addPayment, getPayments, getRegistrations, approveRegistration, deleteRegistration } from '../utils/database';
import { Plus, Search, Edit2, Trash2, X, Phone, Mail, UserPlus, CheckCircle } from 'lucide-react';
/* eslint-disable no-unused-vars */

const EMPTY = { name: '', classId: '', parentName: '', parentPhone: '', parentEmail: '', enrollDate: new Date().toISOString().slice(0,10), status: 'active' };

export default function Students() {
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null); // null | 'add' | 'edit'
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const [filter, setFilter] = useState('all');
  const [tab, setTab] = useState('enrolled'); // 'enrolled' | 'registrations'

  const students = getStudents();
  const classes = getClasses();
  const payments = getPayments();
  const registrations = getRegistrations();

  const visible = students.filter(s => {
    const q = search.toLowerCase();
    const match = s.name.toLowerCase().includes(q) || s.parentName?.toLowerCase().includes(q);
    const statusMatch = filter === 'all' || s.status === filter;
    return match && statusMatch;
  });

  const openAdd = () => { setForm(EMPTY); setModal('add'); };
  const openEdit = (s) => { setForm(s); setEditId(s.id); setModal('edit'); };
  const closeModal = () => { setModal(null); setEditId(null); };

  const save = () => {
    if (!form.name || !form.classId) return alert('Name and class are required');
    if (modal === 'add') {
      const newStudent = addStudent(form);
      const cls = classes.find(c => c.id === form.classId);
      const month = new Date().toISOString().slice(0, 7);
      addPayment({ studentId: newStudent.id, month, amount: cls?.monthlyFee || 0, status: 'pending', paidDate: null, dueDate: `${month}-01`, method: null, notes: '' });
    } else {
      updateStudent(editId, form);
    }
    closeModal();
    setRefresh(r => r + 1);
  };

  const remove = (id) => {
    if (window.confirm('Delete this student and all their payment records?')) {
      deleteStudent(id);
      setRefresh(r => r + 1);
    }
  };

  const [approveModal, setApproveModal] = useState(null);
  const [approveClassId, setApproveClassId] = useState('');

  const handleApprove = () => {
    if (!approveClassId) return alert('Please select a class');
    const cls = classes.find(c => c.id === approveClassId);
    approveRegistration(approveModal, approveClassId, cls?.monthlyFee || 0);
    setApproveModal(null);
    setApproveClassId('');
    setRefresh(r => r + 1);
  };

  const getStudentBalance = (studentId) => {
    return payments.filter(p => p.studentId === studentId && p.status === 'pending').reduce((s, p) => s + p.amount, 0);
  };

  return (
    <div>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '2px solid var(--cream-dark)' }}>
        <button onClick={() => setTab('enrolled')} style={{
          padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer',
          fontFamily: 'var(--font-body)', fontSize: '0.9rem', fontWeight: 500,
          color: tab === 'enrolled' ? 'var(--green-main)' : 'var(--text-light)',
          borderBottom: tab === 'enrolled' ? '2px solid var(--green-main)' : '2px solid transparent',
          marginBottom: -2, transition: 'all 0.2s',
        }}>
          Enrolled Students
        </button>
        <button onClick={() => setTab('registrations')} style={{
          padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer',
          fontFamily: 'var(--font-body)', fontSize: '0.9rem', fontWeight: 500,
          color: tab === 'registrations' ? 'var(--green-main)' : 'var(--text-light)',
          borderBottom: tab === 'registrations' ? '2px solid var(--green-main)' : '2px solid transparent',
          marginBottom: -2, transition: 'all 0.2s',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <UserPlus size={15} />
          New Registrations
          {registrations.length > 0 && (
            <span style={{ background: 'var(--clay)', color: '#fff', borderRadius: 20, padding: '1px 8px', fontSize: '0.72rem', fontWeight: 600 }}>
              {registrations.length}
            </span>
          )}
        </button>
      </div>

      {/* Registrations Tab */}
      {tab === 'registrations' ? (
        <div>
          {registrations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-light)' }}>
              <div style={{ fontSize: '3rem', marginBottom: 12 }}>📋</div>
              <p>No pending registrations. New parents can register via the public form.</p>
            </div>
          ) : (
            <div className="card">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Child Name</th>
                      <th>Age</th>
                      <th>Parent</th>
                      <th>Phone</th>
                      <th>Email</th>
                      <th>Registered</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registrations.map(reg => (
                      <tr key={reg.id} style={{ background: 'var(--warning-light)' }}>
                        <td><strong>{reg.childName}</strong></td>
                        <td>{reg.childAge || '—'}</td>
                        <td>{reg.parentName}</td>
                        <td><a href={`tel:${reg.parentPhone}`} style={{ color: 'var(--green-mid)' }}>{reg.parentPhone}</a></td>
                        <td>{reg.parentEmail && <a href={`mailto:${reg.parentEmail}`} style={{ color: 'var(--green-mid)', fontSize: '0.82rem' }}>{reg.parentEmail}</a>}</td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--text-light)' }}>{reg.registeredAt ? new Date(reg.registeredAt).toLocaleDateString() : '—'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button className="btn btn-success btn-sm" onClick={() => setApproveModal(reg.id)}>
                              <CheckCircle size={13} /> Approve & Assign
                            </button>
                            <button className="btn btn-danger btn-sm btn-icon" onClick={() => { if (window.confirm('Delete this registration?')) { deleteRegistration(reg.id); setRefresh(r => r + 1); } }}>
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Approve Modal */}
          {approveModal && (
            <div className="modal-overlay" onClick={() => setApproveModal(null)}>
              <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 400 }}>
                <div className="modal-header">
                  <span className="modal-title">Assign to Class</span>
                  <button className="btn btn-ghost btn-icon" onClick={() => setApproveModal(null)}><X size={16} /></button>
                </div>
                <p style={{ color: 'var(--text-light)', fontSize: '0.88rem', marginBottom: 20 }}>
                  Select a class to assign this child. They will be moved from registrations to enrolled students.
                </p>
                <div className="form-group">
                  <label className="form-label">Class *</label>
                  <select className="form-select" value={approveClassId} onChange={e => setApproveClassId(e.target.value)}>
                    <option value="">Select a class…</option>
                    {classes.map(c => <option key={c.id} value={c.id}>{c.name} — SAR {c.monthlyFee}/mo</option>)}
                  </select>
                </div>
                <div className="modal-actions">
                  <button className="btn btn-ghost" onClick={() => setApproveModal(null)}>Cancel</button>
                  <button className="btn btn-success" onClick={handleApprove}><CheckCircle size={14} /> Confirm & Enroll</button>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
      {/* Header actions */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
        <div className="search-bar">
          <Search size={15} />
          <input placeholder="Search students or parents…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="form-select" style={{ width: 'auto' }} value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button className="btn btn-primary" onClick={openAdd} style={{ marginLeft: 'auto' }}>
          <Plus size={15} /> Add Student
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student Name</th>
                <th>Class</th>
                <th>Parent</th>
                <th>Contact</th>
                <th>Enrolled</th>
                <th>Balance Due</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-light)' }}>No students found</td></tr>
              )}
              {visible.map(s => {
                const cls = classes.find(c => c.id === s.classId);
                const balance = getStudentBalance(s.id);
                return (
                  <tr key={s.id}>
                    <td><strong>{s.name}</strong></td>
                    <td>
                      <span style={{ background: cls?.color + '22', color: cls?.color, padding: '3px 10px', borderRadius: 20, fontSize: '0.78rem', fontWeight: 600 }}>
                        {cls?.name || '—'}
                      </span>
                    </td>
                    <td>{s.parentName}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {s.parentPhone && <a href={`tel:${s.parentPhone}`} style={{ color: 'var(--green-mid)' }}><Phone size={14} /></a>}
                        {s.parentEmail && <a href={`mailto:${s.parentEmail}`} style={{ color: 'var(--green-mid)' }}><Mail size={14} /></a>}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{s.enrollDate}</td>
                    <td>
                      {balance > 0
                        ? <span style={{ color: '#dc2626', fontWeight: 600 }}>SAR {balance.toLocaleString()}</span>
                        : <span style={{ color: 'var(--success)' }}>✓ Clear</span>}
                    </td>
                    <td>
                      <span className={`badge ${s.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(s)}><Edit2 size={13} /></button>
                        <button className="btn btn-danger btn-sm btn-icon" onClick={() => remove(s.id)}><Trash2 size={13} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{modal === 'add' ? 'Add New Student' : 'Edit Student'}</span>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={16} /></button>
            </div>

            <div className="form-group">
              <label className="form-label">Student Full Name *</label>
              <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Layla Al-Rashid" />
            </div>

            <div className="form-group">
              <label className="form-label">Class *</label>
              <select className="form-select" value={form.classId} onChange={e => setForm({ ...form, classId: e.target.value })}>
                <option value="">Select a class…</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name} — SAR {c.monthlyFee}/mo</option>)}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Parent / Guardian Name</label>
                <input className="form-input" value={form.parentName} onChange={e => setForm({ ...form, parentName: e.target.value })} placeholder="Full name" />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.parentPhone} onChange={e => setForm({ ...form, parentPhone: e.target.value })} placeholder="+966…" />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Parent Email</label>
              <input className="form-input" type="email" value={form.parentEmail} onChange={e => setForm({ ...form, parentEmail: e.target.value })} placeholder="email@example.com" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Enrollment Date</label>
                <input className="form-input" type="date" value={form.enrollDate} onChange={e => setForm({ ...form, enrollDate: e.target.value })} />
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
              <button className="btn btn-primary" onClick={save}>{modal === 'add' ? 'Add Student' : 'Save Changes'}</button>
            </div>
          </div>
          </div>
        )}
        </>
      )}
    </div>
  );
}
