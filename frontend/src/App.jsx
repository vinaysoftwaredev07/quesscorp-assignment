import { Navigate, Route, Routes } from 'react-router-dom';
import PropTypes from 'prop-types';

import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/DashboardPage';
import EmployeePage from './pages/EmployeePage';
import AttendancePage from './pages/AttendancePage';
import SignInPage from './pages/SignInPage';
import { getStoredAdminKey } from './utils/auth';


function ProtectedRoute({ children }) {
  const isAuthenticated = Boolean(getStoredAdminKey());
  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;
  }
  return children;
}

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
};

function App() {
  const isAuthenticated = Boolean(getStoredAdminKey());

  return (
    <Routes>
      <Route path="/signin" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <SignInPage />} />
      <Route
        element={(
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        )}
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/employees" element={<EmployeePage />} />
        <Route path="/attendance" element={<AttendancePage />} />
      </Route>
      <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/signin'} replace />} />
    </Routes>
  );
}

export default App;
