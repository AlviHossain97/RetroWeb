import { X, Heart, Trash2, ImageIcon, FileText, HardDrive, Clock, Calendar, Gamepad2, Download } from "lucide-react";
import type { Game } from "../lib/storage/db";
import SessionStartButton from "./SessionStartButton";
import DownloadButton from "./DownloadButton";
import { getSystemLabel } from "../lib/library/title-utils";

// Suppress unused import warning - Download icon used as type check
void Download;

interface GameDetailsDrawerProps {
  game: Game | null;
  onClose: () => void;
  onLaunch: (game: Game) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
  onRemove: (id: string) => void;
  onSetCover?: (id: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(ts: number | undefined): string {
  if (!ts) return 'Never';
  return new Date(ts).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatPlaytime(ms: number | undefined): string {
  if (!ms) return 'Not played';
  const hours = Math.floor(ms / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

const SYSTEM_GRADIENTS: Record<string, string> = {
  nes: 'linear-gradient(135deg, #e53e3e, #fc8181)',
  snes: 'linear-gradient(135deg, #805ad5, #b794f4)',
  gb: 'linear-gradient(135deg, #2b6cb0, #63b3ed)',
  gbc: 'linear-gradient(135deg, #276749, #68d391)',
  gba: 'linear-gradient(135deg, #2c5282, #90cdf4)',
  genesis: 'linear-gradient(135deg, #2d3748, #718096)',
  psx: 'linear-gradient(135deg, #1a365d, #4299e1)',
  n64: 'linear-gradient(135deg, #276749, #38a169)',
};

export default function GameDetailsDrawer({ game, onClose, onLaunch, onToggleFavorite, onRemove, onSetCover }: GameDetailsDrawerProps) {
  const isOpen = game !== null;
  const gradient = game ? (SYSTEM_GRADIENTS[game.system] || 'linear-gradient(135deg, #2d3748, #4a5568)') : '';

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
          style={{ animation: 'fadeSlideIn 0.2s ease' }}
        />
      )}

      {/* Drawer */}
      <div
        className="fixed top-0 right-0 h-full z-50 w-full max-w-sm flex flex-col overflow-hidden"
        style={{
          background: 'var(--surface-1)',
          borderLeft: '1px solid var(--border-strong)',
          boxShadow: 'var(--shadow-lg)',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {game && (
          <>
            {/* Cover art header */}
            <div className="relative shrink-0" style={{ height: 200 }}>
              {game.coverUrl ? (
                <img src={game.coverUrl} alt={game.title} className="absolute inset-0 w-full h-full object-cover" />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center" style={{ background: gradient }}>
                  <Gamepad2 size={64} className="text-white/40" strokeWidth={1} />
                </div>
              )}
              {/* Overlay gradient for readability */}
              <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(26,26,36,1) 0%, transparent 60%)' }} />

              {/* Close button */}
              <button
                onClick={onClose}
                className="absolute top-3 right-3 p-2 rounded-full transition-colors"
                style={{ background: 'rgba(0,0,0,0.5)', color: 'var(--text-primary)' }}
              >
                <X size={18} />
              </button>

              {/* Favorite button */}
              <button
                onClick={() => onToggleFavorite(game.id, !game.isFavorite)}
                className="absolute top-3 left-3 p-2 rounded-full transition-colors"
                style={{ background: 'rgba(0,0,0,0.5)', color: game.isFavorite ? '#f6c90e' : 'var(--text-muted)' }}
              >
                <Heart size={18} fill={game.isFavorite ? 'currentColor' : 'none'} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5">
              {/* Title and system */}
              <div className="mb-5">
                <h2 className="text-xl font-bold leading-tight mb-2" style={{ color: 'var(--text-primary)' }}>
                  {game.displayTitle || game.title}
                </h2>
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wide"
                    style={{ background: 'var(--accent-primary)', color: '#fff' }}
                  >
                    {getSystemLabel(game.system)}
                  </span>
                  {game.size && (
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {formatBytes(game.size)}
                    </span>
                  )}
                </div>
              </div>

              {/* Primary action */}
              <div className="mb-3">
                <SessionStartButton onClick={() => onLaunch(game)} label="Launch Game" size="md" />
              </div>

              {/* Download button */}
              <div className="mb-5">
                <DownloadButton
                  onClick={() => {}}
                  disabled={!game.hasLocalRom}
                  label={game.hasLocalRom ? "Download ROM" : "No Local ROM"}
                />
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 mb-5">
                {[
                  { icon: <Clock size={14} />, label: 'Last Played', value: formatDate(game.lastPlayed) },
                  { icon: <Calendar size={14} />, label: 'Added', value: formatDate(game.addedAt) },
                  { icon: <HardDrive size={14} />, label: 'Playtime', value: formatPlaytime(game.playtime) },
                  { icon: <FileText size={14} />, label: 'Core', value: game.core || '—' },
                ].map(stat => (
                  <div key={stat.label} className="p-3 rounded-lg" style={{ background: 'var(--surface-2)' }}>
                    <div className="flex items-center gap-1.5 mb-1" style={{ color: 'var(--text-muted)' }}>
                      {stat.icon}
                      <span className="text-[10px] font-bold uppercase tracking-wider">{stat.label}</span>
                    </div>
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* File metadata */}
              <div className="mb-5 p-3 rounded-lg" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-soft)' }}>
                <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>File Info</p>
                <p className="text-xs font-mono break-all" style={{ color: 'var(--text-secondary)' }}>{game.filename}</p>
              </div>

              {/* Quick actions */}
              <div className="flex flex-col gap-2">
                {onSetCover && (
                  <button
                    onClick={() => onSetCover(game.id)}
                    className="flex items-center gap-2 w-full px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
                    style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
                  >
                    <ImageIcon size={16} />
                    Set Cover Art
                  </button>
                )}
                <button
                  onClick={() => { onRemove(game.id); onClose(); }}
                  className="flex items-center gap-2 w-full px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
                  style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}
                >
                  <Trash2 size={16} />
                  Remove from Library
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
