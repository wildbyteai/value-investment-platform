import type { paths } from "./api-schema";
type Path = keyof paths;
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
// mode "session": identity comes from the HttpOnly cookie; only the workspace is sent.
// mode "dev": local mock identities via X-Vip-Login (the server refuses it in production).
export const session = { login: "research@demo", workspace: "", mode: "session" as "session" | "dev" };
export function authHeaders(): Record<string, string> {
  const h: Record<string, string> = { "X-Requested-With": "vip", "X-Vip-Workspace": session.workspace };
  if (session.mode === "dev") h["X-Vip-Login"] = session.login;
  return h;
}
export async function api(path: Path | string, options: RequestInit = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
  }).catch(() => {
    throw new ApiError(0, "无法连接本地服务，请检查服务后重试");
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new ApiError(
      response.status,
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail
              .map(
                (e: any) => `${e.loc?.slice(1).join(".") || "输入"}：${e.msg}`,
              )
              .join("；")
          : "请求未完成，请检查输入后重试",
    );
  return data;
}
export const post = (
  path: Path | string,
  data: unknown,
  headers?: Record<string, string>,
) => api(path, { method: "POST", body: JSON.stringify(data), headers });
