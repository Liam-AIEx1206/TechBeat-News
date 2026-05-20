import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export async function POST() {
  const session = await auth();
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Skip Supabase sync if not configured (local dev)
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey  = process.env.SUPABASE_SERVICE_KEY;
  if (!supabaseUrl || !serviceKey || supabaseUrl.includes("your-project")) {
    return NextResponse.json({ ok: true, skipped: "supabase_not_configured" });
  }

  const { createClient } = await import("@supabase/supabase-js");
  const supabaseAdmin = createClient(supabaseUrl, serviceKey);

  const { email, name, image } = session.user;
  const { error } = await supabaseAdmin
    .from("users")
    .upsert({ email, name, avatar_url: image }, { onConflict: "email" });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
