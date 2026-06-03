import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/generate-composition" : "http://backend:8000/generate-composition";
  
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

  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
