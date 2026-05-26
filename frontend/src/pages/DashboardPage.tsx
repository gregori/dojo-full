import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Dashboard</h1>
        <button
          onClick={handleLogout}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Logout
        </button>
      </div>

      <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h2>User Info</h2>
        <p><strong>Name:</strong> {user.name}</p>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Roles:</strong> {user.roles.join(', ')}</p>
        <p><strong>Organization:</strong> {user.org_id}</p>
      </div>

      <div>
        <h2>Navigation</h2>
        {user.roles.includes('instructor') || user.roles.includes('super-admin') ? (
          <div style={{ marginTop: '1rem' }}>
            <p><a href="#students">Manage Students</a> (coming soon)</p>
            <p><a href="#classes">Manage Classes</a> (coming soon)</p>
            <p><a href="#exams">Manage Exams</a> (coming soon)</p>
          </div>
        ) : (
          <div style={{ marginTop: '1rem' }}>
            <p><a href="#attendance">My Attendance</a> (coming soon)</p>
          </div>
        )}
        {user.roles.includes('super-admin') && (
          <div style={{ marginTop: '1rem' }}>
            <p><a href="#users">Manage Users</a> (coming soon)</p>
          </div>
        )}
      </div>
    </div>
  );
}