import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getTeachers, getStudents, getClasses, getAttendanceForDate, markAttendance, getAttendanceReport } from '../utils/database';
import { Calendar, CheckCircle2, XCircle, Clock, BarChart3, Users, ClipboardList } from 'lucide-react';

export default function Attendance() {
  const { user } = useAuth();
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [tab, setTab] = useState('mark');

  const teachers = getTeachers();
  const teacher = teachers.find(t => t.email === user?.email);
  const classId = teacher?.classId;
  const students = getStudents().filter(s => s.status === 'active' && s.classId === classId);
  const classes = getClasses();
  const cls = classes.find(c => c.id === classId);
  const dayRecords = getAttendanceForDate(date);

  if (!teacher) {
    return (
      <div className="empty-state">
        <ClipboardList size={48} />
        <h3>No teacher profile linked</h3>
        <p>Your account email does not match any teacher record.</p>
      </div>
    );
  }

  if (tab === 'reports') {
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <BarChart3 size={20} />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', color: 'var(--green-deep)' }}>Attendance Report</h2>
          {cls && <span className="badge badge-blue">{cls.name}</span>}
          <button className="btn btn-ghost btn-sm" onClick={() => setTab('mark')}>
            <ClipboardList size={14} /> Back to Marking
          </button>
        </div>
        {students.length === 0 ? (
          <div className="empty-state"><BarChart3 size={48} /><h3>No data</h3><p>No students to report on.</p></div>
        ) : (
          <div className="card"><div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrap"><table>
              <thead><tr><th>Student</th><th>Days</th><th>Present</th><th>Absent</th><th>Excused</th><th>Rate</th></tr></thead>
              <tbody>
                {students.map(s => {
                  const r = getAttendanceReport(s.id);
                  const c = r.rate >= 80 ? 'var(--success)' : r.rate >= 60 ? 'var(--warning)' : 'var(--danger)';
                  return (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong></td>
                      <td>{r.total}</td>
                      <td style={{ color: 'var(--success)' }}>{r.present}</td>
                      <td style={{ color: 'var(--danger)' }}>{r.absent}</td>
                      <td style={{ color: 'var(--clay-light)' }}>{r.excused}</td>
                      <td><span style={{ fontWeight: 700, color: c }}>{r.rate}%</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table></div>
          </div></div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Calendar size={18} />
          <input type="date" className="form-input" style={{ width: 180 }} value={date} onChange={e => setDate(e.target.value)} />
        </div>
        {cls && <span className="badge badge-blue">{cls.name}</span>}
        <button className="btn btn-secondary btn-sm" onClick={() => setTab('reports')}>
          <BarChart3 size={14} /> View Reports
        </button>
      </div>

      {students.length === 0 ? (
        <div className="empty-state"><Users size={48} /><h3>No students in your class</h3><p>There are no active students assigned to {cls?.name || 'your class'}.</p></div>
      ) : (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Students — {date}</h3>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-light)' }}>{students.length} students</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrap"><table>
              <thead><tr><th>Student</th><th>Parent</th><th style={{ width: 220 }}>Status</th></tr></thead>
              <tbody>
                {students.map(s => {
                  const r = dayRecords.find(a => a.studentId === s.id);
                  const status = r?.status || '';
                  return (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong></td>
                      <td style={{ color: 'var(--text-light)', fontSize: '0.82rem' }}>{s.parentName}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6 }}>
                          {['present', 'absent', 'excused'].map(st => (
                            <button key={st}
                              className={`btn btn-sm ${status === st ? (st === 'present' ? 'btn-success' : st === 'absent' ? 'btn-danger' : 'btn-ghost') : 'btn-ghost'}`}
                              onClick={() => { markAttendance(s.id, date, st); }}
                              style={status === st ? {} : { opacity: 0.6 }}
                            >
                              {st === 'present' ? <CheckCircle2 size={14} /> : st === 'absent' ? <XCircle size={14} /> : <Clock size={14} />}
                              {st.charAt(0).toUpperCase() + st.slice(1)}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table></div>
          </div>
        </div>
      )}
    </div>
  );
}