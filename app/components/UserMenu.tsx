"use client";

import { signOut, useSession } from "next-auth/react";
import { useEffect, useRef, useState } from "react";

export function UserMenu() {
  const { data: session } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (session?.user) {
      fetch("/api/auth/sync-user", { method: "POST" }).catch(() => {});
    }
  }, [session?.user?.email]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleSignOut() {
    // NextAuth v5 beta: get CSRF token first then POST signout form
    try {
      const csrfRes = await fetch("/api/auth/csrf");
      const { csrfToken } = await csrfRes.json();
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/api/auth/signout";
      const tokenInput = document.createElement("input");
      tokenInput.type = "hidden";
      tokenInput.name = "csrfToken";
      tokenInput.value = csrfToken;
      const callbackInput = document.createElement("input");
      callbackInput.type = "hidden";
      callbackInput.name = "callbackUrl";
      callbackInput.value = "/login";
      form.appendChild(tokenInput);
      form.appendChild(callbackInput);
      document.body.appendChild(form);
      form.submit();
    } catch {
      window.location.href = "/api/auth/signout";
    }
  }

  if (!session?.user) return null;

  const { name, email, image } = session.user;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "5px 5px 5px 12px", borderRadius: "var(--r-full)",
          background: open ? "var(--gray-2)" : "transparent",
          border: "1px solid var(--gray-3)",
          cursor: "pointer", transition: "all 0.2s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--gray-2)")}
        onMouseLeave={(e) => { if (!open) e.currentTarget.style.background = "transparent"; }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-6)" }}>
          {name?.split(" ").pop()}
        </span>
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt={name ?? ""} width={28} height={28}
            style={{ borderRadius: "50%", border: "1px solid var(--gray-3)" }} />
        ) : (
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: "var(--accent)", display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 12, fontWeight: 900, color: "var(--black)",
          }}>
            {name?.[0]?.toUpperCase() ?? "U"}
          </div>
        )}
      </button>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0,
          width: 220, background: "var(--gray-1)",
          border: "1px solid var(--gray-3)", borderRadius: "var(--r-lg)",
          boxShadow: "0 16px 48px rgba(0,0,0,0.5)",
          overflow: "hidden", animation: "fade-up 0.2s var(--ease-out) both",
          zIndex: 200,
        }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--gray-3)" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--white)", marginBottom: 2 }}>{name}</div>
            <div style={{ fontSize: 11, color: "var(--gray-5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{email}</div>
          </div>

          <div style={{ padding: 6 }}>
            <a href="/history"
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "9px 12px", borderRadius: "var(--r)",
                fontSize: 13, fontWeight: 600, color: "var(--gray-6)",
                textDecoration: "none", transition: "all 0.15s",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--gray-2)"; (e.currentTarget as HTMLElement).style.color = "var(--white)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "var(--gray-6)"; }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "currentColor", flexShrink: 0 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              Lịch sử video
            </a>

            <div style={{ height: 1, background: "var(--gray-3)", margin: "6px 0" }} />

            <button
              onClick={handleSignOut}
              style={{
                width: "100%", display: "flex", alignItems: "center", gap: 10,
                padding: "9px 12px", borderRadius: "var(--r)",
                fontSize: 13, fontWeight: 600, color: "var(--red)",
                background: "transparent", border: "none", cursor: "pointer",
                transition: "background 0.15s", textAlign: "left",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(239,68,68,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "currentColor", flexShrink: 0 }}>
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Đăng xuất
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
