"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { getGmailStatus, getGmailLoginUrl } from "@/lib/endpoints";

interface GmailConnectProps {
  onClose?: () => void;
}

export const GmailConnect = ({ onClose }: GmailConnectProps) => {
  const statusQuery = useQuery({
    queryKey: ["gmail-status"],
    queryFn: getGmailStatus,
  });

  const handleConnect = async () => {
    try {
      const { loginUrl } = await getGmailLoginUrl();
      window.location.href = loginUrl;
    } catch {
      // Not configured
    }
  };

  const connected = statusQuery.data?.connected ?? false;
  const configured = statusQuery.data?.configured ?? false;

  return (
    <motion.div
      className="rounded-xl border border-white/70 bg-white/60 p-4 shadow-lg backdrop-blur-md"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
          Gmail
        </h3>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:bg-white/60 hover:text-slate-700"
            aria-label="Close"
          >
            ×
          </button>
        )}
      </div>

      <div className="mt-3">
        <AnimatePresence mode="wait">
          {!configured ? (
            <p className="text-xs text-slate-600">
              Gmail not configured. Set <code className="rounded bg-slate-200/80 px-1">GMAIL_CLIENT_ID</code>,{" "}
              <code className="rounded bg-slate-200/80 px-1">GMAIL_CLIENT_SECRET</code>, and{" "}
              <code className="rounded bg-slate-200/80 px-1">GMAIL_REDIRECT_URI</code> in .env
            </p>
          ) : connected ? (
            <motion.div
              key="connected"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-sm font-medium text-slate-800">Connected</span>
              </div>
              <p className="text-xs text-slate-600">
                Gmail is connected. You can read and send mail from the app.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="disconnected"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p className="mb-3 text-xs text-slate-600">
                Connect your Gmail account to read and send emails.
              </p>
              <motion.button
                type="button"
                onClick={handleConnect}
                className="rounded-full border border-white/85 bg-gradient-to-r from-red-500/85 to-rose-500/85 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white shadow-md hover:from-red-600 hover:to-rose-600"
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
              >
                Connect Gmail
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};
