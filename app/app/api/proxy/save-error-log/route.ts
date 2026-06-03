import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev ? "http://localhost:8000/save-error-log" : "http://backend:8000/save-error-log";

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const userEmail = req.headers.get("x-user-email");
  if (userEmail) {
    headers["x-user-email"] = userEmail;
  }

  const body = await req.json();

  const response = await fetch(backendUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
