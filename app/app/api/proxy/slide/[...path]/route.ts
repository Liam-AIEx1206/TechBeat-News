import { NextRequest } from "next/server";

// Catch-all proxy: XNEW frontend → slide-engine (:8100). Forward mọi method,
// giữ nguyên body/headers/query; stream response nên chạy được cả JSON, SSE
// (/events), tải file (export pptx/pdf/png-zip) và file tĩnh (/fs, trang HTML).
const BASE = process.env.NODE_ENV === "development"
  ? "http://localhost:8100"
  : "http://slide-engine:8100";

async function handle(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = `${BASE}/${(path || []).map(encodeURIComponent).join("/")}${req.nextUrl.search}`;

  const headers: Record<string, string> = {};
  const ct = req.headers.get("content-type");
  if (ct) headers["content-type"] = ct;
  const accept = req.headers.get("accept");
  if (accept) headers["accept"] = accept;
  const userEmail = req.headers.get("x-user-email");
  if (userEmail) headers["x-user-email"] = userEmail;

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: hasBody ? await req.arrayBuffer() : undefined,
    // @ts-expect-error duplex bắt buộc khi có body stream trên Node fetch
    duplex: "half",
  });

  const respHeaders = new Headers();
  for (const key of ["content-type", "content-disposition", "cache-control", "content-length"]) {
    const v = upstream.headers.get(key);
    if (v) respHeaders.set(key, v);
  }
  // SSE cần không buffer
  if (upstream.headers.get("content-type")?.includes("event-stream")) {
    respHeaders.set("Cache-Control", "no-cache, no-transform");
    respHeaders.set("X-Accel-Buffering", "no");
  }

  return new Response(upstream.body, { status: upstream.status, headers: respHeaders });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
export const PATCH = handle;
