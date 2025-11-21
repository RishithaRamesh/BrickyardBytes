import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import PrivateRoute from './routes/PrivateRoute';

//Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Broadcast from './pages/Broadcast';
import YourRuns from './pages/YourRuns';
import Profile from './pages/Profile';
import History from './pages/History';
import RunDetails from './pages/RunDetails';

//Components
import Navbar from './components/Navbar';
import Footer from "./components/Footer";
import ChatbotLauncher from './components/ChatbotLauncher';

function Layout({ children }) {
  const location = useLocation();
  const hideNavbar = ['/login', '/register'].includes(location.pathname);
  return (
    <>
      {!hideNavbar && <Navbar />}
      <main>{children}</main>
      {!hideNavbar && <Footer/>}
      <ChatbotLauncher />
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Layout>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/" element={
            <PrivateRoute>
              <Home /> {/* Shows available and joined runs */}
            </PrivateRoute>
          } />
          <Route path="/your-runs" element={
            <PrivateRoute>
              <YourRuns />
            </PrivateRoute>}/>
          <Route path="/your-runs/:id" element={
            <PrivateRoute>
              <RunDetails />
            </PrivateRoute>
          } />


          <Route path="/broadcast" element={
            <PrivateRoute>
              <Broadcast /> 
            </PrivateRoute>
          } />
          <Route path="/profile" element={
            <PrivateRoute>
              <Profile />
            </PrivateRoute>
          } />
          <Route path="/history" element={
            <PrivateRoute>
              <History />
            </PrivateRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
          </Layout>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
