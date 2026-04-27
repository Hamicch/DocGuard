import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { env, hasSupabaseEnv } from "@/lib/env";

const PROTECTED_PREFIXES = ["/runs", "/settings"];

export async function updateSession(request: NextRequest) {
  if (!hasSupabaseEnv) {
    return NextResponse.next({ request });
  }

  let response = NextResponse.next({
    request,
  });

  const supabase = createServerClient(env.supabaseUrl, env.supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const requiresAuth = PROTECTED_PREFIXES.some((prefix) => request.nextUrl.pathname.startsWith(prefix));
  if (requiresAuth && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  if (request.nextUrl.pathname === "/login" && user) {
    const url = request.nextUrl.clone();
    url.pathname = "/runs";
    return NextResponse.redirect(url);
  }

  return response;
}
