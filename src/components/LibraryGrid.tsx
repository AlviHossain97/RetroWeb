import React, { useMemo } from "react";
import { VirtuosoGrid } from "react-virtuoso";
import { LayoutGrid, List, Gamepad2, Star, Play } from "lucide-react";
import type { Game } from "../lib/storage/db";
import GameCard from "./GameCard";
import { getSystemLabel } from "../lib/library/title-utils";

interface LibraryGridProps {
  games: Game[];
  viewMode: "grid" | "list";
  onViewModeChange: (mode: "grid" | "list") => void;
  onLaunch: (game: Game) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
  onRemove: (id: string) => void;
  onSetCover?: (id: string) => void;
}

type VirtuosoListProps = {
  style?: React.CSSProperties;
  children?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>;

export default function LibraryGrid({
  games,
  viewMode,
  onViewModeChange,
  onLaunch,
  onToggleFavorite,
  onRemove,
  onSetCover,
}: LibraryGridProps) {
  const listGames = useMemo(() => games, [games]);

  if (!games.length) return null;

  return (
    <div className="flex flex-col w-full h-full flex-1">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">My Library</h2>
          <span className="text-sm text-muted-foreground font-mono bg-secondary px-2.5 py-1 rounded-lg">
            {games.length}
          </span>
        </div>
        <div className="bg-secondary flex rounded-lg overflow-hidden border border-border p-0.5">
          <button
            onClick={() => onViewModeChange("grid")}
            className={`px-3 py-2 rounded-md transition-all ${
              viewMode === "grid"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="Grid View"
          >
            <LayoutGrid size={16} />
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className={`px-3 py-2 rounded-md transition-all ${
              viewMode === "list"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="List View"
          >
            <List size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-[500px]">
        {viewMode === "grid" ? (
          <VirtuosoGrid
            style={{ height: "100%" }}
            totalCount={games.length}
            overscan={20}
            components={{
              List: React.forwardRef<HTMLDivElement, VirtuosoListProps>(({ style, children, ...props }, ref) => (
                <div
                  ref={ref}
                  {...props}
                  style={{
                    ...style,
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                    gap: "1.25rem",
                    paddingBottom: "2rem",
                  }}
                >
                  {children}
                </div>
              )),
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
                />
              );
            }}
          />
        ) : (
          <div className="flex flex-col gap-2 pb-8 h-full">
            {listGames.map((game) => (
              <div
                key={game.id}
                className="flex items-center justify-between px-4 bg-card h-[68px] border border-border hover:border-primary/40 transition-all cursor-pointer group rounded-xl card-hover"
                style={{ boxShadow: "var(--shadow-sm)" }}
                onClick={() => onLaunch(game)}
              >
                <div className="flex items-center gap-4 flex-1 overflow-hidden">
                  <div className="w-12 h-12 bg-[var(--surface-1)] rounded-lg flex items-center justify-center shrink-0 overflow-hidden">
                    {game.coverUrl ? (
                      <img src={game.coverUrl} alt={game.title} className="w-full h-full object-cover" />
                    ) : (
                      <Gamepad2 size={22} className="text-muted-foreground/40" strokeWidth={1.5} />
                    )}
                  </div>
                  <h4 className="font-medium text-foreground text-sm truncate flex-1 group-hover:text-primary transition-colors">
                    {game.displayTitle || game.title}
                  </h4>
                  <p className="text-xs text-muted-foreground w-32 shrink-0 truncate uppercase tracking-wider font-semibold">
                    {getSystemLabel(game.system)}
                  </p>
                  <p className="text-xs text-muted-foreground w-32 shrink-0 hidden sm:block">
                    {game.lastPlayed ? "Played recently" : "Never played"}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-4 shrink-0">
                  {game.isFavorite && <Star size={16} className="text-[var(--warning)]" fill="currentColor" />}
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <Play size={14} className="text-primary ml-0.5" fill="currentColor" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
