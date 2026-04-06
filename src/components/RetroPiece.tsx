interface RetroPieceProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function RetroPiece({ className = "", size = "md" }: RetroPieceProps) {
  const classes = ["retro-piece", `retro-piece--${size}`, className].filter(Boolean).join(" ");

  return (
    <span className={classes} aria-hidden="true">
      <span className="retro-piece__block" />
      <span className="retro-piece__block" />
      <span className="retro-piece__block" />
      <span className="retro-piece__block" />
    </span>
  );
}
