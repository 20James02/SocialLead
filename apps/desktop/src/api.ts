import { invoke } from "@tauri-apps/api/core";

export type Connection = { baseUrl: string; token: string };
let connection: Connection = { baseUrl: "http://127.0.0.1:8765", token: "" };
export function configure(next: Connection) {
  const url = new URL(next.baseUrl);
  if (
    url.protocol !== "http:" ||
    url.hostname !== "127.0.0.1" ||
    url.username ||
    url.password ||
    url.pathname !== "/"
  )
    throw new Error("Địa chỉ engine phải là http://127.0.0.1:<port>");
  connection = { baseUrl: url.origin, token: next.token };
}
export async function desktopConnection(): Promise<Connection | null> {
  if (!("__TAURI_INTERNALS__" in window)) return null;
  const result = await invoke<Connection>("engine_connection");
  configure(result);
  return result;
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${connection.baseUrl}/api/v1${path}`, {
    method,
    headers: {
      "X-App-Session-Token": connection.token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message =
      typeof error.detail === "string"
        ? error.detail
        : Array.isArray(error.detail)
          ? error.detail
              .map(
                (d: { msg: string; loc: string[] }) =>
                  `${d.loc.slice(1).join(".")}: ${d.msg}`,
              )
              .join("; ")
          : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export async function exportCustomers() {
  const response = await fetch(
    `${connection.baseUrl}/api/v1/export/customers`,
    { headers: { "X-App-Session-Token": connection.token } },
  );
  if (!response.ok) throw new Error("Không xuất được danh sách khách hàng");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "scansocial-customers.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function liveFeed(
  onEvent: (type: string) => void,
  onState: (online: boolean) => void,
) {
  let socket: WebSocket | null = null,
    retry: ReturnType<typeof setTimeout> | undefined,
    ping: ReturnType<typeof setInterval> | undefined,
    closed = false;
  const connect = () => {
    socket = new WebSocket(
      `${connection.baseUrl.replace("http:", "ws:")}/ws/live?token=${encodeURIComponent(connection.token)}`,
    );
    socket.onopen = () => {
      onState(true);
      ping = setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
      }, 20000);
    };
    socket.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data).event_type);
      } catch {
        /* Ignore invalid envelopes. */
      }
    };
    socket.onclose = () => {
      onState(false);
      clearInterval(ping);
      if (!closed) retry = setTimeout(connect, 3000);
    };
    socket.onerror = () => socket?.close();
  };
  connect();
  return () => {
    closed = true;
    clearTimeout(retry);
    clearInterval(ping);
    socket?.close();
  };
}
