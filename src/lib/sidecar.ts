import { invoke } from "@tauri-apps/api/core";

export class SidecarError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SidecarError";
  }
}

export async function sendToSidecar(message: object): Promise<object> {
  const raw = await invoke<string>("send_to_sidecar", { message: JSON.stringify(message) });
  const response = JSON.parse(raw) as Record<string, unknown>;
  if (response.type === "error") {
    throw new SidecarError((response.message as string) ?? "Unknown sidecar error");
  }
  return response;
}
