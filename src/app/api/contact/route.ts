import { NextResponse } from "next/server";

type ContactData = {
  name: string;
  email: string;
  phone: string;
  childAge: string;
  program: string;
  message: string;
};

// Rate limiting store (in-memory, resets on server restart)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW = 60 * 60 * 1000; // 1 hour
const MAX_REQUESTS_PER_WINDOW = 5;

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  if (rateLimitMap.size > 1000) {
    for (const [key, entry] of rateLimitMap) {
      if (now > entry.resetTime) rateLimitMap.delete(key);
    }
  }
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return true;
  }

  if (record.count >= MAX_REQUESTS_PER_WINDOW) {
    return false;
  }

  record.count++;
  return true;
}

function text(value: unknown, maxLength: number): string {
  return typeof value === "string" ? value.trim().slice(0, maxLength) : "";
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
  }[character] ?? character));
}

function safeSubjectName(value: string): string {
  return value.replace(/[\r\n]+/g, " ").slice(0, 120);
}

async function sendEmailViaResend(data: ContactData) {
  const RESEND_API_KEY = process.env.RESEND_API_KEY;

  if (!RESEND_API_KEY) {
    throw new Error("RESEND_API_KEY not configured");
  }

  const name = escapeHtml(data.name);
  const email = escapeHtml(data.email);
  const phone = escapeHtml(data.phone);
  const childAge = escapeHtml(data.childAge);
  const program = escapeHtml(data.program);
  const message = escapeHtml(data.message);

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${RESEND_API_KEY}`,
    },
    body: JSON.stringify({
      from: process.env.CONTACT_EMAIL_FROM || "noreply@montessori-ksa.com",
      to: process.env.CONTACT_EMAIL_TO || "info@montessori-ksa.com",
      subject: `رسالة جديدة من ${safeSubjectName(data.name)}`,
      html: `
        <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
          <h2 style="color: #059669; border-bottom: 2px solid #059669; padding-bottom: 10px;">رسالة جديدة من نموذج الاتصال</h2>

          <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 20px;">
            <p style="margin: 10px 0;"><strong>الاسم:</strong> ${name}</p>
            <p style="margin: 10px 0;"><strong>البريد الإلكتروني:</strong> <a href="mailto:${email}">${email}</a></p>
            <p style="margin: 10px 0;"><strong>رقم الهاتف:</strong> <a href="tel:${phone}">${phone}</a></p>
            ${childAge ? `<p style="margin: 10px 0;"><strong>عمر الطفل:</strong> ${childAge}</p>` : ''}
            ${program ? `<p style="margin: 10px 0;"><strong>البرنامج المهتم به:</strong> ${program}</p>` : ''}

            <div style="margin-top: 20px; padding: 15px; background-color: #f3f4f6; border-left: 4px solid #059669; border-radius: 4px;">
              <p style="margin: 0; font-weight: bold; color: #059669;">الرسالة:</p>
              <p style="margin: 10px 0; line-height: 1.6;">${message}</p>
            </div>
          </div>

          <div style="margin-top: 20px; padding: 15px; background-color: #e0f2fe; border-radius: 8px; font-size: 12px; color: #0369a1;">
            <p style="margin: 0;"><strong>تم الإرسال في:</strong> ${new Date().toLocaleString('ar-SA', { timeZone: 'Asia/Riyadh' })}</p>
          </div>
        </div>
      `,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Resend API error: ${error}`);
  }

  return response.json();
}

export async function POST(request: Request) {
  try {
    // Get client IP for rate limiting
    const ip = request.headers.get("x-forwarded-for") ||
               request.headers.get("x-real-ip") ||
               "unknown";

    // Check rate limit
    if (!checkRateLimit(ip)) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    const body = await request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
    }

    const name = text(body.name, 120);
    const email = text(body.email, 254).toLowerCase();
    const phone = text(body.phone, 32);
    const childAge = text(body.childAge, 20);
    const program = text(body.program, 80);
    const message = text(body.message, 4000);

    // Validate required fields
    if (!name || !email || !phone || !message) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: "Invalid email address" },
        { status: 400 }
      );
    }

    // Phone validation (basic)
    const phoneRegex = /^[+]?[\d\s()-]{10,}$/;
    if (!phoneRegex.test(phone)) {
      return NextResponse.json(
        { error: "Invalid phone number" },
        { status: 400 }
      );
    }

    console.log("Contact form submission received", {
      timestamp: new Date().toISOString(),
      ip: ip !== "unknown" ? ip.substring(0, 10) + "..." : ip,
    });

    // Try to send email if Resend is configured
    if (process.env.RESEND_API_KEY) {
      try {
        await sendEmailViaResend({
          name,
          email,
          phone,
          childAge,
          program,
          message,
        });

        console.log("✅ Email sent successfully via Resend");

        return NextResponse.json({
          success: true,
          message: "Message sent successfully!",
        });
      } catch (emailError) {
        console.error("❌ Email sending failed:", emailError);

        // Still return success to user, but log the error
        return NextResponse.json({
          success: true,
          message: "Message received. We'll contact you soon!",
        });
      }
    } else {
      // Email service not configured
      console.warn("⚠️ RESEND_API_KEY not configured. Form data logged only.");

      return NextResponse.json({
        success: true,
        message: "Form received successfully. Email integration pending.",
      });
    }

  } catch (error) {
    console.error("❌ Contact form error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
