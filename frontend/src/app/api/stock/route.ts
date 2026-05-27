import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const RENDER_API_URL = "https://market-structure-platform.onrender.com";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const ticker = searchParams.get("ticker")?.trim().toUpperCase();

  if (!ticker) {
    return NextResponse.json({ error: "ticker is required" }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${RENDER_API_URL}/stock/${encodeURIComponent(ticker)}`, {
      cache: "no-store",
    });
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (error) {
    return NextResponse.json({
      error: error instanceof Error ? error.message : "stock proxy failed",
    }, { status: 502 });
  }
}
