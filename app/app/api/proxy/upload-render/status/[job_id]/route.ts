import { NextRequest, NextResponse } from "next/server";

export async function GET(
  req: NextRequest,
  { params }: { params: { job_id: string } }
) {
  const isDev = process.env.NODE_ENV === "development";
  const backendUrl = isDev
    ? `http://localhost:8000/upload-render/status/${params.job_id}`
    : `http://backend:8000/upload-render/status/${params.job_id}`;

  const headers: Record<string, string> = {};
  const userEmail = req.headers.get("x-user-email");
  if (userEmail) headers["x-user-email"] = userEmail;

  const response = await fetch(backendUrl, { headers });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
