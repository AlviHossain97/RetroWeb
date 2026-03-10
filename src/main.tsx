import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from "react-router";
import './index.css'
import App from './App.tsx'

const Home = lazy(() => import('./routes/home.tsx'))
const Library = lazy(() => import('./routes/index.tsx'))
const Play = lazy(() => import('./routes/play.tsx'))
const Systems = lazy(() => import('./routes/systems.tsx'))
const Settings = lazy(() => import('./routes/settings.tsx'))
const BiosVault = lazy(() => import('./routes/bios.tsx'))
const SavesVault = lazy(() => import('./routes/saves.tsx'))
const Login = lazy(() => import('./routes/login.tsx'))
const ControllerTest = lazy(() => import('./routes/controller.tsx'))
const Chat = lazy(() => import('./routes/chat.tsx'))
const AchievementsPage = lazy(() => import('./routes/achievements.tsx'))
const StatsPage = lazy(() => import('./routes/stats.tsx'))
const RomHacksPage = lazy(() => import('./routes/romhacks.tsx'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }} />
        </div>
      }>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<App />}>
            <Route index element={<Home />} />
            <Route path="library" element={<Library />} />
            <Route path="systems" element={<Systems />} />
            <Route path="game/:id" element={<div>Game Details</div>} />
            <Route path="play" element={<Play />} />
            <Route path="bios" element={<BiosVault />} />
            <Route path="saves" element={<SavesVault />} />
            <Route path="controller" element={<ControllerTest />} />
            <Route path="chat" element={<Chat />} />
            <Route path="achievements" element={<AchievementsPage />} />
            <Route path="stats" element={<StatsPage />} />
            <Route path="romhacks" element={<RomHacksPage />} />
            <Route path="settings" element={<Settings />} />
            <Route path="help/chd" element={<div>CHD Conversion Guide</div>} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
)
