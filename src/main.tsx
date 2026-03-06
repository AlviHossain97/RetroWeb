import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from "react-router";
import './index.css'
import App from './App.tsx'
import Library from './routes/index.tsx'
import Play from './routes/play.tsx'
import Systems from './routes/systems.tsx'
import Settings from './routes/settings.tsx'
import BiosVault from './routes/bios.tsx'
import SavesVault from './routes/saves.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Library />} />
          <Route path="systems" element={<Systems />} />
          <Route path="game/:id" element={<div>Game Details</div>} />
          <Route path="play" element={<Play />} />
          <Route path="bios" element={<BiosVault />} />
          <Route path="saves" element={<SavesVault />} />
          <Route path="settings" element={<Settings />} />
          <Route path="help/chd" element={<div>CHD Conversion Guide</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
