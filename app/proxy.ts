import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const isLoginPage = req.nextUrl.pathname.startsWith("/login");
  const isApiAuth = req.nextUrl.pathname.startsWith("/api/auth");

  // Allow auth API routes always
  if (isApiAuth) return NextResponse.next();

  // Redirect to home (/) if visiting login page directly
  if (isLoginPage) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin));
  }

  // Redirect to home (/) if visiting any protected page (like /history) while not logged in
  const isProtectedPage = req.nextUrl.pathname.startsWith("/history");
  if (!isLoggedIn && isProtectedPage) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin));
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
