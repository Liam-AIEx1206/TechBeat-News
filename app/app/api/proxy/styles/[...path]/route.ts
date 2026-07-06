import { NextRequest } from "next/server";

// GET /api/proxy/styles/<id>/preview → serve preview.html của style (pass-through).
export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const isDev = process.env.NODE_ENV === "development";
  const base = isDev ? "http://localhost:8000/styles" : "http://backend:8000/styles";
  const backendUrl = `${base}/${(path || []).map(encodeURIComponent).join("/")}`;
  try {
    const res = await fetch(backendUrl);
    const body = await res.arrayBuffer();
    return new Response(body, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") || "text/html; charset=utf-8" },
    });
  } catch {
    return new Response("", { status: 502 });
  }
}
