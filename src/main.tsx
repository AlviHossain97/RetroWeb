import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from "react-router";
import './index.css'
import App from './App.tsx'

const Home = lazy(() => import('./routes/home.tsx'))
const Library = lazy(() => import('./routes/index.tsx'))
const Systems = lazy(() => import('./routes/systems.tsx'))
const Settings = lazy(() => import('./routes/settings.tsx'))
const ControllerTest = lazy(() => import('./routes/controller.tsx'))
const Chat = lazy(() => import('./routes/chat.tsx'))
const AchievementsPage = lazy(() => import('./routes/achievements.tsx'))
const StatsPage = lazy(() => import('./routes/stats.tsx'))
const Dashboard = lazy(() => import('./routes/dashboard.tsx'))
const Sessions = lazy(() => import('./routes/sessions.tsx'))
const Games = lazy(() => import('./routes/games.tsx'))
const Devices = lazy(() => import('./routes/devices.tsx'))
const Admin = lazy(() => import('./routes/admin.tsx'))
const Kiosk = lazy(() => import('./routes/kiosk.tsx'))
const BackgroundView = lazy(() => import('./routes/background.tsx'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }} />
        </div>
      }>
        <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<Home />} />
            <Route path="library" element={<Library />} />
            <Route path="systems" element={<Systems />} />
            <Route path="controller" element={<ControllerTest />} />
            <Route path="chat" element={<Chat />} />
            <Route path="achievements" element={<AchievementsPage />} />
            <Route path="stats" element={<StatsPage />} />
            <Route path="settings" element={<Settings />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="sessions" element={<Sessions />} />
            <Route path="games" element={<Games />} />
            <Route path="devices" element={<Devices />} />
            <Route path="background" element={<BackgroundView />} />
            <Route path="admin" element={<Admin />} />
          </Route>
          <Route path="/kiosk" element={<Kiosk />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
)
