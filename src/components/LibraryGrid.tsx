import React, { useMemo } from "react";
import { VirtuosoGrid } from "react-virtuoso";
import { LayoutGrid, List, Star, MoreVertical, Gamepad2 } from "lucide-react";
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
        <h2 className="text-[28px] font-bold tracking-tight text-foreground">My Library</h2>
        <div className="bg-muted flex rounded-md overflow-hidden border border-border">
          <button
            onClick={() => onViewModeChange("grid")}
            className={`px-3 py-2 transition-colors ${viewMode === "grid" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            title="Grid View"
          >
            <LayoutGrid size={18} />
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className={`px-3 py-2 transition-colors ${viewMode === "list" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            title="List View"
          >
            <List size={18} />
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
              List: React.forwardRef<HTMLDivElement, VirtuosoListProps>(({ style, children, ...props }, ref) => {
                return (
                  <div
                    ref={ref}
                    {...props}
                    style={{
                      ...style,
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                      gap: "2rem",
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
                />
              );
            }}
          />
        ) : (
          <div className="flex flex-col gap-4 pb-8 h-full pr-2">
            {listGames.map((game) => (
              <div
                key={game.id}
                className="flex items-center justify-between px-4 bg-card h-[64px] border border-border hover:border-primary transition-colors cursor-pointer group rounded-md mb-2 shadow-sm"
                onClick={() => onLaunch(game)}
              >
                <div className="flex items-center gap-4 flex-1 overflow-hidden">
                  <div className="w-12 h-12 bg-[#111111] rounded-sm flex items-center justify-center shrink-0">
                    {game.coverUrl ? (
                      <img src={game.coverUrl} alt={game.title} className="w-full h-full object-cover rounded-sm" />
                    ) : (
                      <Gamepad2 size={24} className="text-muted-foreground" strokeWidth={1.5} />
                    )}
                  </div>
                  <h4 className="font-sans font-medium text-foreground text-base truncate flex-1">{game.displayTitle || game.title}</h4>
                  <p className="font-sans text-sm text-muted-foreground w-40 shrink-0 truncate">{getSystemLabel(game.system)}</p>
                  <p className="font-sans text-sm text-muted-foreground w-40 shrink-0 hidden sm:block">
                    {game.lastPlayed ? "Played recently" : "Never played"}
                  </p>
                </div>
                <div className="flex items-center gap-4 ml-4 shrink-0">
                  {game.isFavorite && <Star size={18} className="text-yellow-500" fill="currentColor" />}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // We'll leave the menu functionality out of the list item for brevity but keep the visual icon
                    }}
                    className="p-1 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <MoreVertical size={20} />
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
