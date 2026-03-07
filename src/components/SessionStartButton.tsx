import { Play, Loader2, ChevronRight } from "lucide-react";

interface SessionStartButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function SessionStartButton({ onClick, disabled, loading, label = "Start Session", size = 'md' }: SessionStartButtonProps) {
  const sizeClasses = {
    sm: 'py-2 px-4 text-sm gap-2',
    md: 'py-3 px-6 text-base gap-3',
    lg: 'py-4 px-8 text-lg gap-3',
  };

  const iconSize = size === 'lg' ? 22 : size === 'sm' ? 14 : 18;

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className="relative group border-none bg-transparent p-0 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 w-full"
      style={{ filter: disabled ? 'grayscale(0.5)' : undefined }}
    >
      {/* Shadow layer */}
      <span className="absolute inset-0 bg-black/25 rounded-lg translate-y-0.5 transition-transform duration-[600ms] ease-[cubic-bezier(0.3,0.7,0.4,1)] group-hover:translate-y-1 group-hover:duration-[250ms] group-active:translate-y-px" />
      {/* Edge layer */}
      <span className="absolute inset-0 rounded-lg" style={{ background: 'linear-gradient(to left, hsl(0,50%,8%), hsl(0,50%,16%), hsl(0,50%,8%))' }} />
      {/* Face layer */}
      <div
        className={`relative flex items-center justify-center ${sizeClasses[size]} text-white rounded-lg -translate-y-1 transition-transform duration-[600ms] group-hover:-translate-y-1.5 group-hover:duration-[250ms] group-active:-translate-y-0.5 group-hover:brightness-110 font-bold tracking-wide`}
        style={{ background: 'linear-gradient(to right, #cc0000, #e94057, #ff6b35)' }}
      >
        {loading ? (
          <Loader2 size={iconSize} className="animate-spin" />
        ) : (
          <Play size={iconSize} fill="currentColor" />
        )}
        <span>{loading ? 'Loading...' : label}</span>
        {!loading && <ChevronRight size={iconSize} className="opacity-70" />}
      </div>
    </button>
  );
}
