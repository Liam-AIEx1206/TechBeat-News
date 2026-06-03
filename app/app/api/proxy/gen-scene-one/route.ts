import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300; // 5 minutes timeout for LLM generation

export async function POST(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/gen-scene-one" : "http://backend:8000/gen-scene-one";
  
  try {
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: await req.arrayBuffer(),
      // @ts-ignore
      duplex: "half",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error("Error proxying gen-scene-one:", error);
    return NextResponse.json({ detail: error.message || "Proxy error" }, { status: 500 });
  }
}
