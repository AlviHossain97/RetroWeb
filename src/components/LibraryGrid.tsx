import React, { useMemo, useRef, useState, useEffect } from "react";
import { VirtuosoGrid } from "react-virtuoso";
import { LayoutGrid, List, Star, Gamepad2, Box } from "lucide-react";
import type { Game } from "../lib/storage/db";
import GameCard from "./GameCard";
import { getSystemLabel } from "../lib/library/title-utils";

interface LibraryGridProps {
  games: Game[];
  viewMode: "grid" | "list" | "carousel";
  onViewModeChange: (mode: "grid" | "list" | "carousel") => void;
  onLaunch: (game: Game) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
  onRemove: (id: string) => void;
  onSetCover?: (id: string) => void;
  onSelectGame?: (game: Game) => void;
}

type VirtuosoListProps = {
  style?: React.CSSProperties;
  children?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>;

const CAROUSEL_GRADIENTS: Record<string, string> = {
  nes: 'linear-gradient(135deg, #e53e3e 0%, #fc8181 100%)',
  snes: 'linear-gradient(135deg, #805ad5 0%, #b794f4 100%)',
  gb: 'linear-gradient(135deg, #2b6cb0 0%, #63b3ed 100%)',
  gbc: 'linear-gradient(135deg, #276749 0%, #68d391 100%)',
  gba: 'linear-gradient(135deg, #2c5282 0%, #90cdf4 100%)',
  genesis: 'linear-gradient(135deg, #2d3748 0%, #718096 100%)',
  psx: 'linear-gradient(135deg, #1a365d 0%, #4299e1 100%)',
  n64: 'linear-gradient(135deg, #276749 0%, #38a169 100%)',
};

// Carousel component
function CarouselView({ games, onSelect, onLaunch }: { games: Game[]; onSelect: (g: Game) => void; onLaunch: (g: Game) => void }) {
  const [paused, setPaused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const quantity = Math.min(games.length, 12);
  const visibleGames = games.slice(0, quantity);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setSelectedIndex(i => i === null ? 0 : (i + 1) % quantity);
      if (e.key === 'ArrowLeft') setSelectedIndex(i => i === null ? 0 : (i - 1 + quantity) % quantity);
      if (e.key === 'Enter' && selectedIndex !== null) onLaunch(visibleGames[selectedIndex]);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [quantity, selectedIndex, visibleGames, onLaunch]);

  if (quantity === 0) return null;

  // Check for reduced motion
  const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    return (
      <div className="w-full overflow-x-auto pb-4">
        <div className="flex gap-4 px-4 min-w-max">
          {visibleGames.map((game) => (
            <div key={game.id} style={{width: 140}}>
              <GameCard game={game} onLaunch={onLaunch} onToggleFavorite={() => {}} onRemove={() => {}} onSelect={onSelect} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const CARD_W = 120;
  const CARD_H = 160;
  const translateZ = (CARD_W + CARD_H) * 0.9;

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ height: 380, perspective: '1000px' }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div
        ref={innerRef}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: CARD_W,
          height: CARD_H,
          marginTop: -(CARD_H / 2),
          marginLeft: -(CARD_W / 2),
          transformStyle: 'preserve-3d',
          animation: 'carousel-rotate 20s linear infinite',
          animationPlayState: paused ? 'paused' : 'running',
        } as React.CSSProperties}
      >
        {visibleGames.map((game, idx) => {
          const angle = (360 / quantity) * idx;
          const isSelected = selectedIndex === idx;
          const gradient = CAROUSEL_GRADIENTS[game.system] || 'linear-gradient(135deg, #2d3748, #4a5568)';

          return (
            <div
              key={game.id}
              className="absolute overflow-hidden cursor-pointer transition-all duration-200"
              style={{
                width: CARD_W,
                height: CARD_H,
                borderRadius: 12,
                inset: 0,
                transform: `rotateY(${angle}deg) translateZ(${translateZ}px)`,
                border: isSelected ? '2px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.1)',
                boxShadow: isSelected ? '0 0 20px var(--accent-glow)' : '0 4px 16px rgba(0,0,0,0.5)',
              }}
              onClick={() => { setSelectedIndex(idx); onSelect(game); }}
              onDoubleClick={() => onLaunch(game)}
            >
              {game.coverUrl ? (
                <img src={game.coverUrl} alt={game.title} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center" style={{background: gradient}}>
                  <Gamepad2 size={28} className="text-white/40 mb-1" strokeWidth={1.5} />
                  <p className="text-[9px] text-center text-white/60 px-2 leading-tight line-clamp-2">{game.displayTitle || game.title}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Selected game info */}
      {selectedIndex !== null && visibleGames[selectedIndex] && (
        <div
          className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center px-4"
          style={{animation: 'fadeSlideIn 0.3s ease'}}
        >
          <p className="text-sm font-bold" style={{color: 'var(--text-primary)'}}>{visibleGames[selectedIndex].displayTitle || visibleGames[selectedIndex].title}</p>
          <p className="text-[10px] mt-0.5" style={{color: 'var(--text-muted)'}}>Double-click or press Enter to launch</p>
        </div>
      )}
    </div>
  );
}

export default function LibraryGrid({
  games,
  viewMode,
  onViewModeChange,
  onLaunch,
  onToggleFavorite,
  onRemove,
  onSetCover,
  onSelectGame,
}: LibraryGridProps) {
  const listGames = useMemo(() => games, [games]);

  if (!games.length) return null;

  return (
    <div className="flex flex-col w-full h-full flex-1">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold tracking-tight" style={{color: 'var(--text-primary)'}}>My Library</h2>
        <div className="flex rounded-lg overflow-hidden" style={{background: 'var(--surface-2)', border: '1px solid var(--border-soft)'}}>
          <button
            onClick={() => onViewModeChange("carousel")}
            className="px-3 py-2 transition-colors"
            style={{background: viewMode === 'carousel' ? 'var(--accent-primary)' : 'transparent', color: viewMode === 'carousel' ? '#fff' : 'var(--text-muted)'}}
            title="Carousel View"
          >
            <Box size={16} />
          </button>
          <button
            onClick={() => onViewModeChange("grid")}
            className="px-3 py-2 transition-colors"
            style={{background: viewMode === 'grid' ? 'var(--accent-primary)' : 'transparent', color: viewMode === 'grid' ? '#fff' : 'var(--text-muted)'}}
            title="Grid View"
          >
            <LayoutGrid size={16} />
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className="px-3 py-2 transition-colors"
            style={{background: viewMode === 'list' ? 'var(--accent-primary)' : 'transparent', color: viewMode === 'list' ? '#fff' : 'var(--text-muted)'}}
            title="List View"
          >
            <List size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-[500px]">
        {viewMode === "carousel" ? (
          <CarouselView games={games} onSelect={onSelectGame || (() => {})} onLaunch={onLaunch} />
        ) : viewMode === "grid" ? (
          <VirtuosoGrid
            style={{ height: "100%" }}
            totalCount={games.length}
            overscan={20}
            components={{
              List: React.forwardRef<HTMLDivElement, VirtuosoListProps>(({ style, children, ...props }, ref) => {
                return (
                  <div
                    ref={ref}
                    {...props}
                    style={{
                      ...style,
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                      gap: "1.5rem",
                      paddingBottom: "2rem",
                    }}
                  >
                    {children}
                  </div>
                );
              }),
              Item: ({ children, ...props }) => (
                <div {...props} className="w-full">
                  {children}
                </div>
              ),
            }}
            itemContent={(index) => {
              const game = games[index];
              return (
                <GameCard
                  key={game.id}
                  game={game}
                  onLaunch={onLaunch}
                  onToggleFavorite={onToggleFavorite}
                  onRemove={onRemove}
                  onSetCover={onSetCover}
                  onSelect={onSelectGame}
                />
              );
            }}
          />
        ) : (
          <div className="flex flex-col gap-2 pb-8 h-full">
            {listGames.map((game) => (
              <div
                key={game.id}
                className="flex items-center justify-between px-4 h-[60px] cursor-pointer group rounded-lg transition-all duration-150"
                style={{
                  background: 'var(--surface-1)',
                  border: '1px solid var(--border-soft)',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--accent-primary)'; (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-2)'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-soft)'; (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-1)'; }}
                onClick={() => onSelectGame ? onSelectGame(game) : onLaunch(game)}
              >
                <div className="flex items-center gap-3 flex-1 overflow-hidden">
                  <div className="w-10 h-10 rounded-md flex items-center justify-center shrink-0 overflow-hidden" style={{background: 'var(--surface-3)'}}>
                    {game.coverUrl ? (
                      <img src={game.coverUrl} alt={game.title} className="w-full h-full object-cover" />
                    ) : (
                      <Gamepad2 size={18} style={{color: 'var(--text-muted)'}} strokeWidth={1.5} />
                    )}
                  </div>
                  <h4 className="font-medium text-sm truncate flex-1" style={{color: 'var(--text-primary)'}}>{game.displayTitle || game.title}</h4>
                  <p className="text-xs w-32 shrink-0 truncate" style={{color: 'var(--text-secondary)'}}>{getSystemLabel(game.system)}</p>
                  <p className="text-xs w-36 shrink-0 hidden sm:block" style={{color: 'var(--text-muted)'}}>
                    {game.lastPlayed ? `Played ${new Date(game.lastPlayed).toLocaleDateString()}` : 'Never played'}
                  </p>
                  <p className="text-xs w-20 shrink-0 hidden md:block" style={{color: 'var(--text-muted)'}}>
                    {game.size ? `${(game.size / (1024*1024)).toFixed(1)} MB` : '—'}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-3 shrink-0">
                  {game.isFavorite && <Star size={14} style={{color: '#f6c90e'}} fill="#f6c90e" />}
                  <button
                    onClick={(e) => { e.stopPropagation(); onLaunch(game); }}
                    className="px-3 py-1 rounded-md text-xs font-semibold opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{background: 'var(--accent-primary)', color: '#fff'}}
                  >
                    Play
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

