import { NextResponse } from "next/server";

const ODOO_BASE =
  (process.env.NEXT_PUBLIC_ODOO_URL || "https://odoo.montessori-ksa.com").replace(
    /\/+$/,
    ""
  );

async function proxy(request: Request) {
  const url = new URL(request.url);
  const target = `${ODOO_BASE}${url.pathname}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(target, init);
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("connection");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(request: Request) {
  return proxy(request);
}

export async function POST(request: Request) {
  return proxy(request);
}

export async function PUT(request: Request) {
  return proxy(request);
}

export async function PATCH(request: Request) {
  return proxy(request);
}

export async function DELETE(request: Request) {
  return proxy(request);
}

export async function OPTIONS(request: Request) {
  return proxy(request);
}
