import { NextRequest, NextResponse } from "next/server";

// GET /api/proxy/styles → liệt kê style pack từ backend.
export async function GET(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/styles" : "http://backend:8000/styles";
  try {
    const res = await fetch(backendUrl, { headers: { Accept: "application/json" } });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: any) {
    return NextResponse.json({ styles: [], error: error?.message || "Proxy error" }, { status: 500 });
  }
}
