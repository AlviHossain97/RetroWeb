import { Star, Play, ImagePlus, Trash, Gamepad2, MoreVertical } from "lucide-react";
import type { Game } from "../lib/storage/db";
import { useState, useRef, useEffect } from "react";
import { getSystemLabel, getSystemGradient, hasRecentAutoSave } from "../lib/library/title-utils";

interface GameCardProps {
  game: Game;
  onLaunch: (game: Game) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
  onRemove: (id: string) => void;
  onSetCover?: (id: string) => void;
}

export default function GameCard({ game, onLaunch, onToggleFavorite, onRemove, onSetCover }: GameCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const systemLabel = getSystemLabel(game.system);
  const systemGradient = getSystemGradient(game.system);
  const quickResume = hasRecentAutoSave(game.lastAutoSaveAt);

  useEffect(() => {
    if (!showMenu) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showMenu]);

  return (
    <div
      className="group relative bg-card border border-border hover:border-primary/40 flex flex-col cursor-pointer rounded-xl overflow-hidden transition-all duration-300 card-hover"
      style={{ boxShadow: "var(--shadow-card)" }}
      onClick={() => onLaunch(game)}
    >
      {quickResume && (
        <div className="absolute top-3 left-3 z-30">
          <span className="px-2.5 py-1 bg-primary/90 text-[10px] font-bold text-white uppercase tracking-wider rounded-md backdrop-blur-sm"
            style={{ boxShadow: "var(--shadow-glow-primary)" }}>
            Quick Resume
          </span>
        </div>
      )}

      {game.isFavorite && (
        <div className="absolute top-3 right-3 z-30">
          <Star size={18} className="text-[var(--warning)] drop-shadow-md" fill="currentColor" />
        </div>
      )}

      <div className="w-full aspect-[3/4] bg-[var(--surface-1)] flex flex-col items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-30" style={{ background: systemGradient }} />

        {game.coverUrl ? (
          <img
            src={game.coverUrl}
            alt={game.title}
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 relative z-10">
            <Gamepad2 size={40} className="text-muted-foreground/40" strokeWidth={1.5} />
            <span className="text-[10px] text-muted-foreground/50 uppercase tracking-widest font-medium">No Cover</span>
          </div>
        )}

        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-gradient-to-t from-black/80 via-black/40 to-transparent z-20">
          <div className="w-14 h-14 rounded-full bg-primary/90 flex items-center justify-center transform scale-75 group-hover:scale-100 transition-transform duration-300"
            style={{ boxShadow: "var(--shadow-glow-primary)" }}>
            <Play size={24} className="text-white ml-1" fill="currentColor" />
          </div>
        </div>

        <div className="absolute bottom-3 left-3 z-30 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="px-2 py-1 text-[10px] font-bold text-white uppercase tracking-wider rounded-md glass">
            {systemLabel}
          </span>
        </div>
      </div>

      <div className="p-3.5 bg-card flex flex-col gap-1.5 relative">
        <div className="flex justify-between items-start gap-2">
          <h3 className="font-semibold text-foreground text-sm leading-tight line-clamp-1 group-hover:text-primary transition-colors">
            {game.displayTitle || game.title}
          </h3>

          <div className="relative" ref={menuRef} onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="text-muted-foreground hover:text-foreground p-1 -mr-1 rounded-md hover:bg-secondary transition-colors opacity-0 group-hover:opacity-100"
            >
              <MoreVertical size={16} />
            </button>

            {showMenu && (
              <div className="absolute bottom-full right-0 mb-2 w-48 bg-popover border border-border rounded-xl overflow-hidden z-40 animate-in fade-in zoom-in-95 duration-150"
                style={{ boxShadow: "var(--shadow-lg)" }}>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-secondary flex items-center gap-2.5 transition-colors"
                  onClick={(e) => { e.stopPropagation(); setShowMenu(false); onLaunch(game); }}
                >
                  <Play size={14} className="text-primary" /> Play
                </button>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-secondary flex items-center gap-2.5 border-t border-border/50 transition-colors"
                  onClick={(e) => { e.stopPropagation(); setShowMenu(false); onToggleFavorite(game.id, !game.isFavorite); }}
                >
                  <Star size={14} className="text-[var(--warning)]" /> {game.isFavorite ? "Unfavorite" : "Favorite"}
                </button>
                {onSetCover && (
                  <button
                    className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-secondary flex items-center gap-2.5 border-t border-border/50 transition-colors"
                    onClick={(e) => { e.stopPropagation(); setShowMenu(false); onSetCover(game.id); }}
                  >
                    <ImagePlus size={14} className="text-[var(--accent)]" /> Cover Art
                  </button>
                )}
                <button
                  className="w-full text-left px-4 py-2.5 text-sm text-destructive hover:bg-destructive/10 flex items-center gap-2.5 border-t border-border/50 transition-colors"
                  onClick={(e) => { e.stopPropagation(); setShowMenu(false); onRemove(game.id); }}
                >
                  <Trash size={14} /> Remove
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="text-[11px] text-muted-foreground truncate uppercase tracking-wider font-semibold">
          {systemLabel}
        </div>
      </div>
    </div>
  );
}
