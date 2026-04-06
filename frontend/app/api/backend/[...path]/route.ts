import { NextRequest, NextResponse } from "next/server";

import { auth0 } from "@/lib/auth0";

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

const backendBaseUrl = (
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export const runtime = "nodejs";

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const session = await auth0.getSession();

  if (!session) {
    return NextResponse.json({ detail: "Sign in with Auth0 to use the dashboard API." }, { status: 401 });
  }

  let accessToken: string;

  try {
    const tokenResult = await auth0.getAccessToken();
    accessToken = tokenResult.token;
  } catch {
    return NextResponse.json(
      {
        detail:
          "Auth0 did not return an access token. Verify AUTH0_AUDIENCE matches your FastAPI API identifier.",
      },
      { status: 401 }
    );
  }

  const { path } = await context.params;
  const upstreamUrl = new URL(`${backendBaseUrl}/${path.join("/")}`);
  upstreamUrl.search = request.nextUrl.search;

  const requestHeaders = new Headers();
  requestHeaders.set("authorization", `Bearer ${accessToken}`);

  const acceptHeader = request.headers.get("accept");
  if (acceptHeader) {
    requestHeaders.set("accept", acceptHeader);
  }

  const contentTypeHeader = request.headers.get("content-type");
  if (contentTypeHeader) {
    requestHeaders.set("content-type", contentTypeHeader);
  }

  const body =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: requestHeaders,
      body: body && body.length > 0 ? body : undefined,
      cache: "no-store",
    });

    const responseBody = await upstreamResponse.text();
    const responseHeaders = new Headers();
    const responseContentType = upstreamResponse.headers.get("content-type");

    if (responseContentType) {
      responseHeaders.set("content-type", responseContentType);
    }

    return new NextResponse(responseBody, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "The Next.js proxy could not reach the FastAPI backend. Start the backend or update API_BASE_URL.",
      },
      { status: 502 }
    );
  }
}
