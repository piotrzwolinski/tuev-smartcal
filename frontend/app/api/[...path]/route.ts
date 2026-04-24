import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const UPSTREAM = process.env.API_UPSTREAM || "http://localhost:8000";
const API_KEY = process.env.SMARTCAL_API_KEY || "";

async function proxy(req: NextRequest, path: string[]) {
  const search = req.nextUrl.search;
  const url = `${UPSTREAM}/api/${path.join("/")}${search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  if (API_KEY) {
    headers.set("x-api-key", API_KEY);
  }

  const init: RequestInit = {
    method: req.method,
    headers,
    // @ts-expect-error Node fetch extension
    duplex: "half",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = req.body as unknown as BodyInit;
  }

  const upstream = await fetch(url, init);

  const respHeaders = new Headers(upstream.headers);
  respHeaders.delete("content-encoding");
  respHeaders.delete("content-length");
  respHeaders.delete("transfer-encoding");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
