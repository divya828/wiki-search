export type Mode = "ask" | "search";

export interface SearchHit {
  title: string;
  snippet: string;
}

export type Fallback =
  | { type: "summary"; title: string; extract: string; thumbnail: string | null }
  | { type: "search_results"; hits: SearchHit[] }
  | { type: "no_results"; message: string };

export interface SearchResponse {
  fallback: Fallback;
  job_id: string | null;
}

export async function postSearch(query: string, mode: Mode): Promise<SearchResponse> {
  const r = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mode }),
  });
  if (!r.ok) throw new Error(`search failed: ${r.status}`);
  return r.json();
}

export type StreamFrame =
  | { type: "status"; status: string; article?: string; sources?: string[] }
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | { type: "close" };

export function openJobStream(
  jobId: string,
  onFrame: (f: StreamFrame) => void,
  onClose: () => void,
): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/api/jobs/${jobId}/stream`);
  ws.onmessage = (ev) => onFrame(JSON.parse(ev.data));
  ws.onclose = onClose;
  return ws;
}
