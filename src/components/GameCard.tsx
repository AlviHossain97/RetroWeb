import { Star, Play, Settings, Trash, Gamepad2, MoreVertical } from "lucide-react";
import type { Game } from "../lib/storage/db";
import { useState } from "react";
import { getSystemLabel, hasRecentAutoSave } from "../lib/library/title-utils";

interface GameCardProps {
    game: Game;
    onLaunch: (game: Game) => void;
    onToggleFavorite: (id: string, isFavorite: boolean) => void;
    onRemove: (id: string) => void;
    onSetCover?: (id: string) => void;
}

export default function GameCard({ game, onLaunch, onToggleFavorite, onRemove, onSetCover }: GameCardProps) {
    const [showMenu, setShowMenu] = useState(false);
    const systemLabel = getSystemLabel(game.system);
    const quickResume = hasRecentAutoSave(game.lastAutoSaveAt);

    return (
        <div className={`group relative bg-card border transition-colors ${game.lastPlayed && quickResume ? 'border-primary' : 'border-border'} hover:border-primary flex flex-col cursor-pointer rounded-md overflow-hidden shadow-sm`}
            onClick={() => onLaunch(game)}
        >
            {quickResume && (
                <div className="absolute top-2 left-2 z-30">
                    <span className="px-2 py-1 bg-blue-600 text-[10px] font-bold text-white uppercase tracking-wider shadow-sm rounded-sm">
                        SAVE AVAILABLE
                    </span>
                </div>
            )}
            <div className="absolute top-2 right-2 z-30 flex gap-1">
                {game.isFavorite && <Star size={18} className="text-yellow-500 drop-shadow-md" fill="currentColor" />}
            </div>

            <div className="w-full aspect-[3/4] bg-[#111111] flex flex-col items-center justify-center relative overflow-hidden">
                {game.coverUrl ? (
                    <img src={game.coverUrl} alt={game.title} className="absolute inset-0 w-full h-full object-cover" />
                ) : (
                    <Gamepad2 size={48} className="text-neutral-500" strokeWidth={1.5} />
                )}

                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/60 z-20">
                    <Play size={48} className="text-primary transform scale-90 group-hover:scale-100 transition-transform drop-shadow-lg" fill="currentColor" />
                </div>

                {game.lastPlayed && quickResume && (
                    <div className="absolute bottom-2 left-2 z-30">
                        <span className="px-2 py-0.5 bg-primary text-primary-foreground font-bold text-[10px] uppercase tracking-wide rounded-sm">
                            PLAYING
                        </span>
                    </div>
                )}
            </div>

            <div className="p-3 bg-card flex flex-col gap-1 relative border-t border-border">
                <div className="flex justify-between items-start gap-2">
                    <h3 className="font-medium text-foreground text-sm leading-tight line-clamp-1">
                        {game.displayTitle || game.title}
                    </h3>
                    <div className="relative" onClick={(e) => e.stopPropagation()}>
                        <button
                            onClick={() => setShowMenu(!showMenu)}
                            className="text-muted-foreground hover:text-foreground p-1 -mr-1"
                        >
                            <MoreVertical size={16} />
                        </button>

                        {showMenu && (
                            <>
                                <div className="fixed inset-0 z-30" onClick={() => setShowMenu(false)} />
                                <div className="absolute bottom-full right-0 mb-2 w-48 bg-card border border-border shadow-xl z-40 overflow-hidden rounded-md">
                                    <button
                                        className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-muted flex items-center gap-2"
                                        onClick={(e) => { e.stopPropagation(); setShowMenu(false); onLaunch(game); }}
                                    >
                                        <Play size={14} /> Play
                                    </button>
                                    <button
                                        className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-muted flex items-center gap-2 border-t border-border/50"
                                        onClick={(e) => { e.stopPropagation(); setShowMenu(false); onToggleFavorite(game.id, !game.isFavorite); }}
                                    >
                                        <Star size={14} /> {game.isFavorite ? 'Unfavorite' : 'Favorite'}
                                    </button>
                                    {onSetCover && (
                                        <button
                                            className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-muted flex items-center gap-2 border-t border-border/50"
                                            onClick={(e) => { e.stopPropagation(); setShowMenu(false); onSetCover(game.id); }}
                                        >
                                            <Settings size={14} /> Cover Art
                                        </button>
                                    )}
                                    <button
                                        className="w-full text-left px-4 py-2.5 text-sm text-destructive hover:bg-muted flex items-center gap-2 border-t border-border/50"
                                        onClick={(e) => { e.stopPropagation(); setShowMenu(false); onRemove(game.id); }}
                                    >
                                        <Trash size={14} /> Remove
                                    </button>
                                </div>
                            </>
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
