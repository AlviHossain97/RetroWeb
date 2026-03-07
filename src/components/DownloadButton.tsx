import { Download, Loader2 } from "lucide-react";

interface DownloadButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  label?: string;
}

export default function DownloadButton({ onClick, disabled, loading, label = "Download" }: DownloadButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className="relative flex items-center justify-center gap-2 px-6 py-2.5 text-white font-semibold text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 active:scale-95 w-full"
      style={{
        background: 'linear-gradient(0deg, rgba(77,54,208,1) 0%, rgba(132,116,254,1) 100%)',
        borderRadius: '20em',
        boxShadow: disabled ? 'none' : '0 0.7em 1.5em -0.5em rgba(77,54,208,0.75)',
        border: 'none',
      }}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
      <span>{loading ? 'Downloading...' : label}</span>
    </button>
  );
}
