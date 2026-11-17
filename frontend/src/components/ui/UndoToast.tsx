"use client";

import React, { useEffect } from "react";
import { Loader2, Undo2 } from "lucide-react";

const AUTO_DISMISS_MS = 15_000;

interface UndoToastProps {
  message: string;
  isUndoing: boolean;
  onUndo: () => void;
  onDismiss: () => void;
}

/**
 * Bottom toast confirming an applied change, with a one-click undo.
 *
 * @param props - Message, whether the undo is running, and the callbacks.
 * @returns The toast, which dismisses itself after 15 seconds.
 */
export function UndoToast({ message, isUndoing, onUndo, onDismiss }: UndoToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="status"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm shadow-lg"
    >
      <span>{message}</span>
      <button
        onClick={onUndo}
        disabled={isUndoing}
        className="flex items-center gap-1.5 font-semibold text-emerald-300 hover:text-emerald-200 disabled:opacity-50"
      >
        {isUndoing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Undo2 className="w-3.5 h-3.5" />}
        <span>Hoàn tác</span>
      </button>
    </div>
  );
}
