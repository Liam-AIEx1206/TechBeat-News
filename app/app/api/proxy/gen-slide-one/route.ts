import { NextRequest, NextResponse } from "next/server";

// Gen 1 slide gồm LLM sinh SVG + tối đa vài vòng visual-review (render + vision
// LLM sửa lỗi) — có thể mất hơn mức mặc định của gen-scene-one.
export const maxDuration = 300;

export async function POST(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/gen-slide-one" : "http://backend:8000/gen-slide-one";

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const userEmail = req.headers.get("x-user-email");
    if (userEmail) {
      headers["x-user-email"] = userEmail;
    }

    const response = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: await req.arrayBuffer(),
      // @ts-ignore
      duplex: "half",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error("Error proxying gen-slide-one:", error);
    return NextResponse.json({ detail: error.message || "Proxy error" }, { status: 500 });
  }
}
