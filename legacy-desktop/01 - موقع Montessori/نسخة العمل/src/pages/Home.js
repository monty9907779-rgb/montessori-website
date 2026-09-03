import { LayoutDashboard, Users, BookOpen, GraduationCap, CreditCard, BarChart2, Bell, GalleryVertical, MessageCircle, ExternalLink, Share2, Camera, ArrowRight, MapPin } from 'lucide-react';
import { getGalleryItems, getLocation } from '../utils/database';
import FlipBook from '../components/FlipBook';

const sections = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, desc: 'Nursery overview & stats', color: '#23d799' },
  { id: 'students', label: 'Students', icon: Users, desc: 'Manage students & registrations', color: '#7339c0' },
  { id: 'classes', label: 'Classes', icon: BookOpen, desc: 'Classes & fee management', color: '#1282d3' },
  { id: 'teachers', label: 'Teachers', icon: GraduationCap, desc: 'Teaching staff management', color: '#e46126' },
  { id: 'gallery', label: 'Photo Gallery', icon: GalleryVertical, desc: 'Nursery photos & activities', color: '#dd2967' },
  { id: 'payments', label: 'Payments', icon: CreditCard, desc: 'Fee tracking & records', color: '#23d799' },
  { id: 'reminders', label: 'Reminders', icon: Bell, desc: 'Payment follow-ups', color: '#e46126' },
  { id: 'reports', label: 'Reports', icon: BarChart2, desc: 'Financial insights & analytics', color: '#7339c0' },
];

export default function Home({ onNavigate }) {
  const location = getLocation();
  const galleryItems = getGalleryItems().filter(item => item.driveLink);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--cream)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        background: '#fff', borderBottom: '1px solid var(--cream-dark)',
        padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="logo.png" alt="Kawkab Al-Tifl" style={{ height: 36, width: 'auto' }} />
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', color: 'var(--green-deep)', fontWeight: 700, lineHeight: 1.2 }}>Kawkab Al-Tifl</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-light)', letterSpacing: '0.05em' }}>EARLY CHILDHOOD CENTER</div>
          </div>
        </div>
        <nav style={{ display: 'flex', gap: 8 }}>
          {sections.slice(0, 4).map(s => (
            <button key={s.id} onClick={() => onNavigate(s.id)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '8px 14px', borderRadius: 8, fontSize: '0.85rem',
              color: 'var(--text-mid)', fontWeight: 500, transition: 'all 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--cream)'}
              onMouseLeave={e => e.currentTarget.style.background = 'none'}
            >{s.label}</button>
          ))}
        </nav>
      </header>

      {/* Hero */}
      <div style={{
        textAlign: 'center', padding: '60px 24px 40px',
        background: 'linear-gradient(180deg, #fff 0%, var(--cream) 100%)',
      }}>
        <img src="logo.png" alt="Kawkab Al-Tifl Al-Hurr Kindergarten" style={{
          maxWidth: 200, width: '100%', marginBottom: 24,
          filter: 'drop-shadow(0 4px 20px rgba(26,58,10,0.1))',
        }} />
        <h1 style={{
          fontFamily: 'var(--font-display)', fontSize: '2.4rem',
          color: 'var(--green-deep)', lineHeight: 1.2, marginBottom: 8,
        }}>Kawkab Al-Tifl Al-Hurr Kindergarten</h1>
        <p style={{ fontSize: '1.1rem', color: 'var(--text-mid)', fontWeight: 300, marginBottom: 6 }}>
          Kindergarten Management Platform
        </p>
        <a href={location.mapsLink} target="_blank" rel="noopener noreferrer"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.9rem', color: 'var(--accent-blue)', textDecoration: 'none', marginBottom: 32 }}>
          <MapPin size={16} /> {location.address}
        </a>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          {sections.slice(0, 3).map(s => (
            <button key={s.id} onClick={() => onNavigate(s.id)} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: s.color, color: '#fff', border: 'none',
              padding: '12px 24px', borderRadius: 50,
              fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.15)'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)'; }}
            >
              <s.icon size={18} /> {s.label} <ArrowRight size={14} />
            </button>
          ))}
        </div>
      </div>

      {/* Management Portal Cards */}
      <div style={{ padding: '20px 24px 40px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
        <h2 style={{
          fontFamily: 'var(--font-display)', fontSize: '1.4rem',
          color: 'var(--green-deep)', marginBottom: 20, textAlign: 'center',
        }}>Management Portal</h2>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 16,
        }}>
          {sections.map(s => (
            <button key={s.id} onClick={() => onNavigate(s.id)} style={{
              background: '#fff', border: '1px solid var(--cream-dark)',
              borderRadius: 14, padding: '24px 20px', cursor: 'pointer',
              textAlign: 'left', transition: 'all 0.2s',
              boxShadow: 'var(--shadow-sm)',
            }}
              onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--shadow-md)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              <div style={{
                width: 44, height: 44, borderRadius: 12,
                background: s.color + '18', color: s.color,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 14,
              }}>
                <s.icon size={22} />
              </div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', color: 'var(--green-deep)', marginBottom: 4 }}>{s.label}</h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-light)' }}>{s.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Gallery Flip Books Section */}
      {galleryItems.length > 0 && (
        <div style={{ padding: '20px 24px 60px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
          <h2 style={{
            fontFamily: 'var(--font-display)', fontSize: '1.4rem',
            color: 'var(--green-deep)', marginBottom: 20, textAlign: 'center',
          }}>
            <GalleryVertical size={22} style={{ verticalAlign: 'middle', marginRight: 8 }} />
            Photo Albums & Flip Books
          </h2>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 16,
          }}>
            {galleryItems.map(item => (
              <div key={item.id} className="card" style={{ overflow: 'hidden' }}>
                <div style={{
                  width: '100%', height: 180,
                  background: 'var(--green-pale)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  overflow: 'hidden',
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
                </div>
                <div className="card-body" style={{ padding: 16 }}>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', color: 'var(--green-deep)', marginBottom: 4 }}>{item.title}</h3>
                  <p style={{ color: 'var(--text-light)', fontSize: '0.8rem', marginBottom: 12 }}>{item.description}</p>
                  <FlipBook driveLink={item.driveLink} title={item.title} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Location Map Section */}
      <div style={{ padding: '40px 24px', textAlign: 'center', background: 'var(--cream-dark)' }}>
        <h3 style={{ fontFamily: 'var(--font-display)', color: 'var(--green-deep)', fontSize: '1.2rem', marginBottom: 8 }}>
          <MapPin size={20} style={{ verticalAlign: 'middle', marginRight: 6 }} />
          Our Location
        </h3>
        <p style={{ color: 'var(--text-mid)', fontSize: '0.9rem', marginBottom: 16 }}>{location.address}</p>
        <a href={location.mapsLink} target="_blank" rel="noopener noreferrer"
          className="btn btn-primary"
          style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 8 }}
        >
          <MapPin size={16} /> Open in Google Maps
        </a>
      </div>

      {/* Follow Us Footer */}
      <footer style={{
        background: 'var(--green-deep)', padding: '32px 24px',
        textAlign: 'center', marginTop: 'auto',
      }}>
        <h3 style={{ fontFamily: 'var(--font-display)', color: '#fff', fontSize: '1.1rem', marginBottom: 20 }}>
          Follow Us
        </h3>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
          {[
            { icon: Camera, label: 'Instagram', href: '#', color: '#E1306C' },
            { icon: Share2, label: 'Facebook', href: '#', color: '#1877F2' },
            { icon: MessageCircle, label: 'WhatsApp', href: 'https://wa.me/966XXXXXXXXX', color: '#25D366' },
            { icon: ExternalLink, label: 'LinkedIn', href: '#', color: '#0A66C2' },
          ].map(({ icon: Icon, label, href, color }) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'rgba(255,255,255,0.1)', color: '#fff',
                padding: '10px 20px', borderRadius: 50, textDecoration: 'none',
                fontSize: '0.88rem', fontWeight: 500, transition: 'all 0.2s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = color}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            >
              <Icon size={18} /> {label}
            </a>
          ))}
        </div>
        <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', marginTop: 20 }}>
          📍 {location.address} · ✉️ info@montessori-ksa.com
        </p>
      </footer>
    </div>
  );
}