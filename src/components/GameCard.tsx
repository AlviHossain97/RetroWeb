import { Star, Play, Settings, Trash, Gamepad2, MoreVertical } from "lucide-react";
import type { Game } from "../lib/storage/db";
import { useState, useRef, useCallback, memo } from "react";
import { getSystemLabel, hasRecentAutoSave } from "../lib/library/title-utils";

interface GameCardProps {
  game: Game;
  onLaunch: (game: Game) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
  onRemove: (id: string) => void;
  onSetCover?: (id: string) => void;
  onSelect?: (game: Game) => void;
}

const SYSTEM_COLORS: Record<string, string> = {
  nes: '#e53e3e',
  snes: '#805ad5',
  gb: '#2b6cb0',
  gbc: '#276749',
  gba: '#2c5282',
  genesis: '#2d3748',
  psx: '#1a365d',
  n64: '#276749',
};

const SYSTEM_GRADIENTS: Record<string, string> = {
  nes: 'linear-gradient(135deg, #e53e3e 0%, #fc8181 100%)',
  snes: 'linear-gradient(135deg, #805ad5 0%, #b794f4 100%)',
  gb: 'linear-gradient(135deg, #2b6cb0 0%, #63b3ed 100%)',
  gbc: 'linear-gradient(135deg, #276749 0%, #68d391 100%)',
  gba: 'linear-gradient(135deg, #2c5282 0%, #90cdf4 100%)',
  genesis: 'linear-gradient(135deg, #2d3748 0%, #718096 100%)',
  psx: 'linear-gradient(135deg, #1a365d 0%, #4299e1 100%)',
  n64: 'linear-gradient(135deg, #276749 0%, #38a169 100%)',
};

function GameCard({ game, onLaunch, onToggleFavorite, onRemove, onSetCover, onSelect }: GameCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [spotlightStyle, setSpotlightStyle] = useState<React.CSSProperties>({});
  const [tiltStyle, setTiltStyle] = useState<React.CSSProperties>({});
  const cardRef = useRef<HTMLDivElement>(null);
  const systemLabel = getSystemLabel(game.system);
  const quickResume = hasRecentAutoSave(game.lastAutoSaveAt);
  const gradient = SYSTEM_GRADIENTS[game.system] || 'linear-gradient(135deg, #2d3748 0%, #4a5568 100%)';
  const accentColor = SYSTEM_COLORS[game.system] || '#cc0000';

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * -6;
    const rotateY = ((x - centerX) / centerX) * 6;

    setSpotlightStyle({
      background: `radial-gradient(circle at ${x}px ${y}px, rgba(255,255,255,0.08) 0%, transparent 60%)`,
    });
    setTiltStyle({
      transform: `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`,
      transition: 'transform 0.1s ease',
    });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setSpotlightStyle({});
    setTiltStyle({ transform: 'perspective(600px) rotateX(0) rotateY(0) scale(1)', transition: 'transform 0.4s ease' });
  }, []);

  const handleClick = () => {
    if (onSelect) {
      onSelect(game);
    } else {
      onLaunch(game);
    }
  };

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    onLaunch(game);
  };

  return (
    <div
      ref={cardRef}
      className="group relative flex flex-col cursor-pointer rounded-xl overflow-hidden"
      style={{
        background: 'var(--surface-1)',
        border: `1px solid ${quickResume ? accentColor + '60' : 'var(--border-soft)'}`,
        boxShadow: 'var(--shadow-sm)',
        ...tiltStyle,
      }}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {/* Spotlight overlay */}
      <div className="absolute inset-0 z-10 pointer-events-none rounded-xl overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity" style={spotlightStyle} />

      {/* Badges row */}
      <div className="absolute top-2 left-2 z-30 flex gap-1.5">
        {quickResume && (
          <span className="px-2 py-0.5 rounded-sm text-[9px] font-bold uppercase tracking-wider text-white" style={{background: '#2563eb'}}>
            RESUME
          </span>
        )}
      </div>

      {/* Favorite star */}
      <div className="absolute top-2 right-2 z-30" onClick={(e) => { e.stopPropagation(); onToggleFavorite(game.id, !game.isFavorite); }}>
        <button className="p-1 rounded-full transition-colors" style={{background: 'rgba(0,0,0,0.4)'}}>
          <Star
            size={14}
            className="transition-colors"
            style={{color: game.isFavorite ? '#f6c90e' : 'rgba(255,255,255,0.4)'}}
            fill={game.isFavorite ? '#f6c90e' : 'none'}
          />
        </button>
      </div>

      {/* Cover art */}
      <div className="w-full aspect-[3/4] relative overflow-hidden">
        {game.coverUrl ? (
          <img src={game.coverUrl} alt={game.title} className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center" style={{background: gradient}}>
            <Gamepad2 size={40} className="text-white/30 mb-2" strokeWidth={1.5} />
          </div>
        )}

        {/* Play overlay */}
        <div className="absolute inset-0 flex items-center justify-center z-20 opacity-0 group-hover:opacity-100 transition-all duration-200" style={{background: 'rgba(0,0,0,0.55)'}}>
          <div
            className="flex items-center justify-center w-14 h-14 rounded-full scale-90 group-hover:scale-100 transition-transform duration-200"
            style={{background: 'var(--accent-primary)', boxShadow: '0 0 20px var(--accent-glow)'}}
            onDoubleClick={(e) => { e.stopPropagation(); onLaunch(game); }}
            onClick={(e) => { e.stopPropagation(); onLaunch(game); }}
          >
            <Play size={22} fill="white" className="text-white ml-0.5" />
          </div>
        </div>

        {/* System badge at bottom of cover */}
        <div className="absolute bottom-2 left-2 z-20">
          <span
            className="text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider text-white"
            style={{background: accentColor + 'dd', backdropFilter: 'blur(4px)'}}
          >
            {systemLabel}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 flex flex-col gap-1" style={{borderTop: '1px solid var(--border-soft)'}}>
        <div className="flex justify-between items-start gap-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-1 flex-1" style={{color: 'var(--text-primary)'}}>
            {game.displayTitle || game.title}
          </h3>
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1 -mr-1 rounded transition-colors"
              style={{color: 'var(--text-muted)'}}
            >
              <MoreVertical size={14} />
            </button>

            {showMenu && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setShowMenu(false)} />
                <div className="absolute bottom-full right-0 mb-2 w-44 rounded-lg overflow-hidden z-40 shadow-2xl" style={{background: 'var(--surface-3)', border: '1px solid var(--border-strong)'}}>
                  <button className="w-full text-left px-4 py-2.5 text-xs font-medium transition-colors hover:bg-white/5 flex items-center gap-2" style={{color: 'var(--text-primary)'}}
                    onClick={(e) => { e.stopPropagation(); setShowMenu(false); onLaunch(game); }}>
                    <Play size={13} /> Play
                  </button>
                  <button className="w-full text-left px-4 py-2.5 text-xs font-medium transition-colors hover:bg-white/5 flex items-center gap-2" style={{color: 'var(--text-primary)', borderTop: '1px solid var(--border-soft)'}}
                    onClick={(e) => { e.stopPropagation(); setShowMenu(false); onToggleFavorite(game.id, !game.isFavorite); }}>
                    <Star size={13} /> {game.isFavorite ? 'Unfavorite' : 'Favorite'}
                  </button>
                  {onSetCover && (
                    <button className="w-full text-left px-4 py-2.5 text-xs font-medium transition-colors hover:bg-white/5 flex items-center gap-2" style={{color: 'var(--text-primary)', borderTop: '1px solid var(--border-soft)'}}
                      onClick={(e) => { e.stopPropagation(); setShowMenu(false); onSetCover(game.id); }}>
                      <Settings size={13} /> Cover Art
                    </button>
                  )}
                  <button className="w-full text-left px-4 py-2.5 text-xs font-medium transition-colors hover:bg-red-500/10 flex items-center gap-2" style={{color: '#ef4444', borderTop: '1px solid var(--border-soft)'}}
                    onClick={(e) => { e.stopPropagation(); setShowMenu(false); onRemove(game.id); }}>
                    <Trash size={13} /> Remove
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Play info */}
        {game.lastPlayed ? (
          <p className="text-[10px] truncate" style={{color: 'var(--text-muted)'}}>
            Played {new Date(game.lastPlayed).toLocaleDateString()}
          </p>
        ) : (
          <p className="text-[10px]" style={{color: 'var(--text-muted)'}}>Never played</p>
        )}
      </div>
    </div>
  );
}

export default memo(GameCard);
