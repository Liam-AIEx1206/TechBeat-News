"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useSession } from "next-auth/react";

interface HistoryItem {
  id: string;
  title: string;
  html_url: string;
  video_url: string;
  duration: number;
  created_at: string;
}

export default function HistoryPage() {
  const { data: session } = useSession();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null);
  const [activeVideoTitle, setActiveVideoTitle] = useState("");
  
  // HTML viewer modal states
  const [activeHtmlUrl, setActiveHtmlUrl] = useState<string | null>(null);
  const [activeHtmlTitle, setActiveHtmlTitle] = useState("");
  const [htmlContent, setHtmlContent] = useState("");
  const [fetchingHtml, setFetchingHtml] = useState(false);
  const [copied, setCopied] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  function fetchHistory() {
    setLoading(true);
    const headers: Record<string, string> = {};
    if (session?.user?.email) {
      headers["X-User-Email"] = session.user.email;
    }
    fetch(`${API}/history/local`, { headers })
      .then((res) => {
        if (!res.ok) throw new Error("Không thể tải lịch sử dựng video.");
        return res.json();
      })
      .then((data) => {
        setHistory(data.history || []);
        setError("");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Đã xảy ra lỗi khi lấy lịch sử.");
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    fetchHistory();
  }, [session?.user?.email]);

  // Fetch HTML source code when viewer is opened
  useEffect(() => {
    if (!activeHtmlUrl) {
      setHtmlContent("");
      return;
    }
    setFetchingHtml(true);
    const fullUrl = activeHtmlUrl.startsWith("http") ? activeHtmlUrl : `${API}${activeHtmlUrl}`;
    fetch(fullUrl)
      .then((r) => r.text())
      .then((txt) => {
        setHtmlContent(txt);
      })
      .catch((e) => {
        setHtmlContent(`<!-- Lỗi tải source HTML: ${e.message} -->`);
      })
      .finally(() => {
        setFetchingHtml(false);
      });
  }, [activeHtmlUrl]);

  const handleDelete = async (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Bạn có chắc chắn muốn xóa bản tin "${title}"? Hành động này sẽ xóa vĩnh viễn cả video đã render và mã HTML.`)) {
      return;
    }

    try {
      const headers: Record<string, string> = {};
      if (session?.user?.email) {
        headers["X-User-Email"] = session.user.email;
      }
      const res = await fetch(`${API}/history/local/${id}`, {
        method: "DELETE",
        headers,
      });
      const data = await res.json();
      if (data.success) {
        fetchHistory();
      } else {
        alert("Xóa thất bại: " + (data.message ?? "Lỗi không xác định"));
      }
    } catch (err) {
      alert("Lỗi khi kết nối đến máy chủ.");
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(htmlContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filtered = history.filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase())
  );

  // Group items by day
  const groupKeys: Record<string, HistoryItem[]> = {};
  filtered.forEach((item) => {
    const d = new Date(item.created_at);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    let key = "";
    if (d.toDateString() === today.toDateString()) {
      key = "Hôm nay";
    } else if (d.toDateString() === yesterday.toDateString()) {
      key = "Hôm qua";
    } else {
      key = d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
    }

    if (!groupKeys[key]) groupKeys[key] = [];
    groupKeys[key].push(item);
  });

  return (
    <div style={{ minHeight: "100vh", background: "var(--black)", color: "var(--white)", position: "relative" }}>
      {/* Dynamic background styling inspired by page.tsx */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 0,
        background: "radial-gradient(ellipse at center, #0c0515 0%, #000000 70%)",
        pointerEvents: "none",
      }} />

      {/* Grid lines layout */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 0,
        backgroundImage: "radial-gradient(circle, rgba(236,72,153,0.06) 1px, transparent 1px)",
        backgroundSize: "40px 40px", opacity: 0.5,
        pointerEvents: "none",
      }} />

      <header className="site-header" style={{ position: "relative", zIndex: 10 }}>
        <a
          href="/"
          style={{
            display: "flex", alignItems: "center", gap: 12,
            background: "transparent", border: "none", cursor: "pointer", color: "inherit",
            textDecoration: "none",
          }}
        >
          <div className="logo-mark" style={{ background: "var(--accent)" }}>T</div>
          <div style={{ textAlign: "left", lineHeight: 1.1 }}>
            <div style={{ fontSize: 13, fontWeight: 800 }}>
              Tech<span style={{ color: "var(--accent)" }}>Beat</span>
            </div>
            <div style={{ fontSize: 9, color: "var(--gray-5)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 600 }}>
              AI News Studio
            </div>
          </div>
        </a>

        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <h2 style={{ fontSize: 13, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--gray-5)", margin: 0 }}>
            LỊCH SỬ DỰNG BẢN TIN TIN TỨC
          </h2>
        </div>

        <a href="/" className="btn-ghost" style={{ textDecoration: "none", fontSize: 11 }}>
          ← Về Trang Chủ
        </a>
      </header>

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 24px", position: "relative", zIndex: 10 }}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ marginBottom: 40 }}
        >
          <div className="hero-eyebrow" style={{ marginBottom: 14 }}>
            Kho lưu trữ nội dung
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20 }}>
            <div>
              <h1 style={{ fontSize: "clamp(28px, 4vw, 42px)", fontWeight: 900, letterSpacing: "-0.03em", margin: 0 }}>
                Quản lý lịch sử bản tin
              </h1>
              <p style={{ fontSize: 13, color: "var(--gray-5)", marginTop: 6, margin: 0 }}>
                Dưới đây là danh sách toàn bộ code HTML và video MP4 đã sinh theo thời gian thực để check mã hoặc xem lại.
              </p>
            </div>

            {/* Search Input bar */}
            <div style={{ width: "100%", maxWidth: 300 }}>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="🔍 Tìm kiếm tiêu đề bản tin..."
                className="input-dark"
                style={{ padding: "10px 16px", fontSize: 12 }}
              />
            </div>
          </div>
        </motion.div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div className="badge badge-accent badge-dot" style={{ background: "rgba(255,255,255,0.03)" }}>
              <span /> Đang tải danh sách lịch sử dựng video...
            </div>
          </div>
        ) : error ? (
          <div style={{
            padding: "24px", borderRadius: "var(--r)",
            background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.2)",
            color: "var(--red)", textAlign: "center"
          }}>
            ⚠ Lỗi: {error}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{
            padding: "60px 24px", borderRadius: "var(--r-lg)",
            background: "var(--gray-1)", border: "1px solid var(--gray-3)",
            textAlign: "center", color: "var(--gray-5)"
          }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px 0", color: "var(--gray-6)" }}>
              {search ? "Không tìm thấy kết quả phù hợp" : "Chưa có bản tin nào trong lịch sử"}
            </p>
            <p style={{ fontSize: 12, margin: 0 }}>
              {search ? "Thử tìm kiếm với từ khóa khác." : "Hãy tiến hành tạo bản tin đầu tiên ở trang chủ để lưu lịch sử!"}
            </p>
            {!search && (
              <a href="/" className="btn-primary" style={{ marginTop: 20, textDecoration: "none" }}>
                <span>▶ Bắt đầu tạo video ngay</span>
              </a>
            )}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>
            {Object.entries(groupKeys).map(([day, items]) => (
              <div key={day}>
                {/* Date header indicator */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--accent)" }}>
                    📅 {day}
                  </h3>
                  <div className="divider-dotted" style={{ flex: 1 }} />
                  <span style={{ fontSize: 10, color: "var(--gray-5)", fontWeight: 700 }}>
                    {items.length} bản tin
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {items.map((item, idx) => {
                    const videoFullUrl = item.video_url.startsWith("http") ? item.video_url : `${API}${item.video_url}`;
                    
                    return (
                      <motion.div
                        key={item.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: idx * 0.05 }}
                        className="scene-card"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                          gap: 16,
                          padding: "16px 20px",
                          background: "linear-gradient(180deg, var(--gray-1) 0%, rgba(10,10,10,0.8) 100%)",
                        }}
                      >
                        <div style={{ flex: 1, minWidth: 280 }}>
                          <span style={{
                            fontFamily: "var(--font-mono)", fontSize: 10,
                            color: "var(--accent2)", display: "block", marginBottom: 4,
                            fontWeight: 700
                          }}>
                            ⏱️ {new Date(item.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                          </span>
                          <h4 style={{ fontSize: 14, fontWeight: 800, color: "var(--white)", margin: 0, lineHeight: 1.3 }}>
                            {item.title}
                          </h4>
                        </div>

                        {/* Control buttons */}
                        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                          {/* Duration badge */}
                          <div className="badge badge-accent" style={{ background: "rgba(255,255,255,0.03)", borderColor: "var(--gray-3)", color: "var(--gray-6)" }}>
                            ⏱️ {Math.floor(item.duration / 60)}:{(item.duration % 60).toString().padStart(2, '0')}
                          </div>

                          <button
                            onClick={() => {
                              setActiveVideoUrl(videoFullUrl);
                              setActiveVideoTitle(item.title);
                            }}
                            className="btn-primary"
                            style={{
                              padding: "8px 16px", fontSize: 11, background: "var(--accent)", color: "var(--black)"
                            }}
                          >
                            <span>▶ Xem Video</span>
                          </button>

                          <button
                            onClick={() => {
                              setActiveHtmlUrl(item.html_url);
                              setActiveHtmlTitle(item.title);
                            }}
                            className="btn-ghost"
                            style={{ padding: "8px 14px", fontSize: 11 }}
                          >
                            💻 Xem mã HTML
                          </button>

                          <button
                            onClick={(e) => handleDelete(item.id, item.title, e)}
                            className="btn-ghost"
                            style={{
                              padding: "8px 10px", fontSize: 11,
                              borderColor: "rgba(239,68,68,0.2)", color: "var(--red)"
                            }}
                          >
                            ✕ Xóa
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Video Overlay Player Modal */}
      <AnimatePresence>
        {activeVideoUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed", inset: 0, zIndex: 9999,
              background: "rgba(0,0,0,0.85)", backdropFilter: "blur(12px)",
              display: "flex", alignItems: "center", justifyContent: "center",
              padding: 24,
            }}
            onClick={() => setActiveVideoUrl(null)}
          >
            <motion.div
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              style={{
                position: "relative", width: "100%", maxWidth: 960,
                background: "var(--gray-1)", border: "1px solid var(--gray-3)",
                borderRadius: "var(--r-lg)", overflow: "hidden",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{
                padding: "16px 20px", display: "flex", justifyContent: "space-between",
                alignItems: "center", borderBottom: "1px solid var(--gray-3)", background: "rgba(0,0,0,0.3)"
              }}>
                <h3 style={{ fontSize: 14, fontWeight: 800, margin: 0, color: "var(--white)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "80%" }}>
                  {activeVideoTitle}
                </h3>
                <button onClick={() => setActiveVideoUrl(null)} className="btn-ghost" style={{ padding: "4px 10px" }}>
                  ✕ Đóng
                </button>
              </div>
              <video src={activeVideoUrl} controls autoPlay style={{ width: "100%", display: "block" }} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HTML Viewer Modal */}
      <AnimatePresence>
        {activeHtmlUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed", inset: 0, zIndex: 9999,
              background: "rgba(0,0,0,0.85)", backdropFilter: "blur(12px)",
              display: "flex", alignItems: "center", justifyContent: "center",
              padding: 24,
            }}
            onClick={() => setActiveHtmlUrl(null)}
          >
            <motion.div
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              style={{
                position: "relative", width: "100%", maxWidth: 840,
                background: "var(--gray-1)", border: "1px solid var(--gray-3)",
                borderRadius: "var(--r-lg)", overflow: "hidden",
                display: "flex", flexDirection: "column", maxHeight: "85vh"
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{
                padding: "16px 20px", display: "flex", justifyContent: "space-between",
                alignItems: "center", borderBottom: "1px solid var(--gray-3)", background: "rgba(0,0,0,0.3)"
              }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ fontSize: 9, fontWeight: 800, color: "var(--accent)", letterSpacing: "0.08em" }}>SOURCE CODE HTML</span>
                  <h3 style={{ fontSize: 13, fontWeight: 800, margin: "2px 0 0 0", color: "var(--white)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "90%" }}>
                    {activeHtmlTitle}
                  </h3>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button
                    onClick={handleCopy}
                    disabled={fetchingHtml || !htmlContent}
                    className="btn-primary"
                    style={{
                      padding: "6px 12px", fontSize: 11,
                      background: copied ? "var(--green)" : "var(--accent)",
                      color: copied ? "var(--white)" : "var(--black)"
                    }}
                  >
                    <span>{copied ? "✓ Đã copy!" : "📋 Copy mã HTML"}</span>
                  </button>
                  <button onClick={() => setActiveHtmlUrl(null)} className="btn-ghost" style={{ padding: "6px 10px", fontSize: 11 }}>
                    ✕ Đóng
                  </button>
                </div>
              </div>

              {/* Source code display box */}
              <div style={{ flex: 1, overflow: "auto", padding: 20, background: "#020204" }}>
                {fetchingHtml ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200, color: "var(--gray-5)" }}>
                    <div className="badge badge-accent badge-dot"><span /> Đang tải mã nguồn HTML...</div>
                  </div>
                ) : (
                  <pre style={{
                    margin: 0, fontFamily: "var(--font-mono)", fontSize: 11,
                    lineHeight: 1.6, color: "rgba(249,115,22,0.85)", whiteSpace: "pre-wrap"
                  }}>
                    <code>{htmlContent}</code>
                  </pre>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
