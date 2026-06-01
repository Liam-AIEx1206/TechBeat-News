import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  // Always proxy directly to the internal backend container
  const backendUrl = "http://backend:8000/build-video";
  
  const response = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
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
