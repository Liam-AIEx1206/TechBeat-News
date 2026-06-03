import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/upload-render" : "http://backend:8000/upload-render";

  const headers: Record<string, string> = {};
  const userEmail = req.headers.get("x-user-email");
  if (userEmail) {
    headers["x-user-email"] = userEmail;
  }

  // Forward the multipart form data as-is
  const formData = await req.formData();

  const response = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: formData,
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
