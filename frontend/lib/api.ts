import { env } from "@/lib/env";

export type Run = {
  id: string;
  repo_id: string;
  pr_number: number;
  pr_title: string;
  status: "pending" | "running" | "completed" | "failed";
  finding_count: number;
  drift_count: number;
  style_count: number;
  cost_usd: number;
  started_at: string;
  completed_at: string | null;
};

export type Finding = {
  id: string;
  run_id: string;
  finding_type: "doc_drift" | "style_violation" | "convention";
  severity: "high" | "medium" | "low";
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  title: string;
  description: string;
  proposed_fix: string | null;
  user_action: "accepted" | "dismissed" | "ignored" | "custom" | "pending";
};

export type Repo = {
  id: string;
  user_id: string;
  full_name: string;
  github_installation_id: number;
  created_at: string;
};

type RunListResponse = {
  items: Run[];
  total: number;
  page: number;
  page_size: number;
};

type RunDetailResponse = {
  run: Run;
  findings: Finding[];
};

function buildApiUrl(path: string): string {
  const base = env.backendApiBaseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Support either BACKEND_API_URL=http://localhost:8000
  // or BACKEND_API_URL=http://localhost:8000/api
  const pathWithoutDuplicateApi =
    base.endsWith("/api") && normalizedPath.startsWith("/api/")
      ? normalizedPath.replace(/^\/api/, "")
      : normalizedPath;

  return `${base}${pathWithoutDuplicateApi}`;
}

async function api<T>(path: string, accessToken: string, init?: RequestInit): Promise<T> {
  const url = buildApiUrl(path);
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API ${response.status} (${url}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}

export async function getRuns(accessToken: string, page = 1): Promise<RunListResponse> {
  return api<RunListResponse>(`/api/runs?page=${page}&page_size=20`, accessToken);
}

export async function getRun(accessToken: string, runId: string): Promise<RunDetailResponse> {
  return api<RunDetailResponse>(`/api/runs/${runId}`, accessToken);
}

export async function getRepos(accessToken: string): Promise<Repo[]> {
  return api<Repo[]>("/api/repos", accessToken);
}

export async function connectRepo(
  accessToken: string,
  body: { full_name: string; github_installation_id: number },
): Promise<Repo> {
  return api<Repo>("/api/repos", accessToken, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function setFindingAction(
  accessToken: string,
  findingId: string,
  body: { action: "accepted" | "ignored" | "custom"; custom_fix?: string },
): Promise<void> {
  await api(`/api/findings/${findingId}/action`, accessToken, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
