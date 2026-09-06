import { mkdir, readFile, writeFile, rename } from "fs/promises";
import path from "path";
import { tmpdir } from "os";

export type WhatsappAutoReplyState = {
  enabled: boolean;
  updatedAt: string;
};

const stateFilePath =
  process.env.WHATSAPP_AUTO_REPLY_STATE_FILE ||
  path.join(tmpdir(), "montessori-whatsapp-auto-reply.json");

function createState(enabled: boolean): WhatsappAutoReplyState {
  return {
    enabled,
    updatedAt: new Date().toISOString(),
  };
}

async function ensureStateDirectory() {
  await mkdir(path.dirname(stateFilePath), { recursive: true });
}

async function writeState(state: WhatsappAutoReplyState) {
  await ensureStateDirectory();
  const tempFilePath = `${stateFilePath}.${Date.now()}.tmp`;
  await writeFile(tempFilePath, JSON.stringify(state, null, 2), "utf8");
  await rename(tempFilePath, stateFilePath);
}

export async function readWhatsappAutoReplyState(): Promise<WhatsappAutoReplyState> {
  try {
    const raw = await readFile(stateFilePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<WhatsappAutoReplyState>;

    if (typeof parsed.enabled === "boolean") {
      return {
        enabled: parsed.enabled,
        updatedAt:
          typeof parsed.updatedAt === "string"
            ? parsed.updatedAt
            : new Date().toISOString(),
      };
    }
  } catch {
    // Fall through to the default state.
  }

  return createState(true);
}

export async function setWhatsappAutoReplyState(
  enabled: boolean
): Promise<WhatsappAutoReplyState> {
  const state = createState(enabled);
  await writeState(state);
  return state;
}

export async function toggleWhatsappAutoReplyState(): Promise<WhatsappAutoReplyState> {
  const currentState = await readWhatsappAutoReplyState();
  return setWhatsappAutoReplyState(!currentState.enabled);
}
