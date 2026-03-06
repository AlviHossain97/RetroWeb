import { useState } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";

export default function LegalModal() {
    const [isOpen, setIsOpen] = useState(() => {
        const hasSeenModal = localStorage.getItem("retroweb_legal_accepted");
        return !hasSeenModal;
    });

    const handleAccept = () => {
        localStorage.setItem("retroweb_legal_accepted", "true");
        setIsOpen(false);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-card border border-border p-8 max-w-lg w-full rounded-md shadow-2xl relative animate-in fade-in zoom-in duration-300">

                <div className="flex items-center gap-5 mb-8">
                    <div className="p-3 border border-destructive/30 rounded-md bg-[#1A0A0A] text-destructive">
                        <AlertTriangle size={32} />
                    </div>
                    <h2 className="text-3xl font-bold text-foreground">Legal Notice</h2>
                </div>

                <div className="space-y-4 text-muted-foreground font-sans mb-10">
                    <p className="text-[15px] leading-relaxed">
                        Welcome to <strong className="text-foreground font-bold text-lg font-normal">RetroWeb</strong>. Before you begin using this emulator, please read and acknowledge the following:
                    </p>
                    <ul className="list-disc pl-5 space-y-3 text-sm">
                        <li>RetroWeb does NOT host, provide, or distribute any game ROMs or BIOS files.</li>
                        <li>You must legally own the original physical hardware and software for any files you upload.</li>
                        <li>Piracy is strictly prohibited. Do not use this tool to play copyrighted material you do not own.</li>
                        <li>All files uploaded remain entirely on your local device. No data is transmitted to external servers.</li>
                    </ul>
                </div>

                <button
                    onClick={handleAccept}
                    className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 rounded-md text-primary-foreground font-sans text-xs uppercase tracking-widest font-bold py-4 transition-colors shadow-sm"
                >
                    <ShieldCheck size={20} />
                    I Understand & Agree
                </button>
            </div>
        </div>
    );
}
