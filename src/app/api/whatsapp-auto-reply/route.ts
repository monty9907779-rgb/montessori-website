import { NextResponse } from "next/server";
import {
  readWhatsappAutoReplyState,
  setWhatsappAutoReplyState,
  toggleWhatsappAutoReplyState,
} from "@/lib/whatsapp-auto-reply";

export const runtime = "nodejs";

export async function GET() {
  const state = await readWhatsappAutoReplyState();

  return NextResponse.json(state, {
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
    },
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => null);
    const enabled =
      body && typeof body === "object" && !Array.isArray(body) && typeof body.enabled === "boolean"
        ? body.enabled
        : null;

    const state =
      enabled === null
        ? await toggleWhatsappAutoReplyState()
        : await setWhatsappAutoReplyState(enabled);

    return NextResponse.json(state, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
      },
    });
  } catch (error) {
    console.error("Whatsapp auto reply API error:", error);
    return NextResponse.json(
      { error: "Failed to update WhatsApp auto reply state" },
      { status: 500 }
    );
  }
}
