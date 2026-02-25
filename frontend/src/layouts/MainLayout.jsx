import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import Button from '../components/Button';
import { clearStoredAdminKey } from '../utils/auth';

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/employees', label: 'Employees' },
  { to: '/attendance', label: 'Attendance' },
];

function MainLayout() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearStoredAdminKey();
    navigate('/signin', { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4">
          <h1 className="text-lg font-semibold tracking-wide text-slate-800">HRMS Lite</h1>
          <div className="flex items-center gap-3">
            <nav className="flex gap-2">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2 text-sm font-medium transition ${
                      isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <Button variant="secondary" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

export default MainLayout;
