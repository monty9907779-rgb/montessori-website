import { useState } from 'react';
import { getPayments, getStudents, getClasses, markPaymentPaid, addPayment, generateMonthlyInvoices } from '../utils/database';
import { Search, CheckCircle, X, RefreshCw, Plus } from 'lucide-react';

export default function Payments() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [monthFilter, setMonthFilter] = useState('');
  const [payModal, setPayModal] = useState(null);
  const [payMethod, setPayMethod] = useState('cash');
  const [refresh, setRefresh] = useState(0);

  const payments = getPayments();
  const students = getStudents();
  const classes = getClasses();

  const allMonths = [...new Set(payments.map(p => p.month))].sort().reverse();

  const enriched = payments.map(p => {
    const student = students.find(s => s.id === p.studentId);
    const cls = classes.find(c => c.id === student?.classId);
    return { ...p, studentName: student?.name || '?', className: cls?.name || '?', student, cls };
  });

  const visible = enriched.filter(p => {
    const q = search.toLowerCase();
    const matchSearch = p.studentName.toLowerCase().includes(q);
    const matchStatus = statusFilter === 'all' || p.status === statusFilter;
    const matchMonth = !monthFilter || p.month === monthFilter;
    return matchSearch && matchStatus && matchMonth;
  }).sort((a, b) => b.month.localeCompare(a.month));

  const confirmPay = () => {
    markPaymentPaid(payModal, payMethod);
    setPayModal(null);
    setRefresh(r => r + 1);
  };

  const genInvoices = () => {
    generateMonthlyInvoices();
    setRefresh(r => r + 1);
    alert('Monthly invoices generated for all active students!');
  };

  const totalShown = visible.reduce((s, p) => s + p.amount, 0);
  const paidShown = visible.filter(p => p.status === 'paid').reduce((s, p) => s + p.amount, 0);
  const pendingShown = visible.filter(p => p.status === 'pending').reduce((s, p) => s + p.amount, 0);

  return (
    <div>
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { label: 'Total', value: totalShown, color: 'var(--green-deep)' },
          { label: 'Collected', value: paidShown, color: 'var(--success)' },
          { label: 'Pending', value: pendingShown, color: '#dc2626' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: 'var(--warm-white)', border: '1px solid var(--cream-dark)', borderRadius: 10, padding: '14px 20px', flex: 1, minWidth: 150 }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginBottom: 4 }}>{label}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color, fontWeight: 700 }}>SAR {value.toLocaleString()}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="search-bar">
          <Search size={15} />
          <input placeholder="Search student…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="form-select" style={{ width: 'auto' }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Status</option>
          <option value="paid">Paid</option>
          <option value="pending">Pending</option>
        </select>
        <select className="form-select" style={{ width: 'auto' }} value={monthFilter} onChange={e => setMonthFilter(e.target.value)}>
          <option value="">All Months</option>
          {allMonths.map(m => (
            <option key={m} value={m}>{new Date(m + '-01').toLocaleDateString('en', { month: 'long', year: 'numeric' })}</option>
          ))}
        </select>
        <button className="btn btn-secondary" onClick={genInvoices} style={{ marginLeft: 'auto' }}>
          <RefreshCw size={14} /> Generate Monthly
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Class</th>
                <th>Month</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Paid Date</th>
                <th>Method</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 && (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--text-light)' }}>No payments found</td></tr>
              )}
              {visible.map(p => (
                <tr key={p.id} className={p.status === 'pending' ? 'overdue-row' : ''}>
                  <td><strong>{p.studentName}</strong></td>
                  <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{p.className}</td>
                  <td>{new Date(p.month + '-01').toLocaleDateString('en', { month: 'short', year: 'numeric' })}</td>
                  <td style={{ fontWeight: 600 }}>SAR {p.amount.toLocaleString()}</td>
                  <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{p.dueDate}</td>
                  <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{p.paidDate || '—'}</td>
                  <td>
                    {p.method ? (
                      <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>{p.method.replace('_', ' ')}</span>
                    ) : '—'}
                  </td>
                  <td>
                    <span className={`badge ${p.status === 'paid' ? 'badge-success' : 'badge-danger'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td>
                    {p.status === 'pending' && (
                      <button className="btn btn-success btn-sm" onClick={() => { setPayModal(p.id); setPayMethod('cash'); }}>
                        <CheckCircle size={13} /> Mark Paid
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pay Modal */}
      {payModal && (
        <div className="modal-overlay" onClick={() => setPayModal(null)}>
          <div className="modal" style={{ maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Record Payment</span>
              <button className="btn btn-ghost btn-icon" onClick={() => setPayModal(null)}><X size={16} /></button>
            </div>
            <p style={{ color: 'var(--text-light)', fontSize: '0.88rem', marginBottom: 20 }}>
              Select payment method and confirm to mark this payment as received.
            </p>
            <div className="form-group">
              <label className="form-label">Payment Method</label>
              <select className="form-select" value={payMethod} onChange={e => setPayMethod(e.target.value)}>
                <option value="cash">Cash</option>
                <option value="bank_transfer">Bank Transfer</option>
                <option value="card">Card</option>
                <option value="cheque">Cheque</option>
              </select>
            </div>
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setPayModal(null)}>Cancel</button>
              <button className="btn btn-success" onClick={confirmPay}><CheckCircle size={14} /> Confirm Payment</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
