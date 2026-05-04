import { useRef, useState } from "react";
import { openJobStream, postSearch, type Fallback, type Mode } from "./api";
import { AnswerStream } from "./components/AnswerStream";
import { SearchResults } from "./components/SearchResults";
import { SummaryCard } from "./components/SummaryCard";

export default function App() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("ask");
  const [fallback, setFallback] = useState<Fallback | null>(null);
  const [status, setStatus] = useState<string>("");
  const [answer, setAnswer] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  async function runSearch(q: string, m: Mode) {
    wsRef.current?.close();
    setFallback(null);
    setStatus("");
    setAnswer("");
    setSources([]);
    setError(null);

    const res = await postSearch(q, m);
    setFallback(res.fallback);
    if (res.job_id) {
      setStatus("indexing");
      wsRef.current = openJobStream(
        res.job_id,
        (f) => {
          if (f.type === "status") {
            setStatus(f.status);
            if (f.sources) setSources(f.sources);
          } else if (f.type === "token") {
            setAnswer((prev) => prev + f.text);
          } else if (f.type === "error") {
            setError(f.message);
          }
        },
        () => {
          wsRef.current = null;
        },
      );
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) runSearch(query.trim(), mode);
  }

  function onPickHit(title: string) {
    setQuery(title);
    runSearch(title, "ask");
  }

  return (
    <div className="app">
      <header>
        <h1>Wiki Search</h1>
      </header>
      <form onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything or search Wikipedia"
          autoFocus
        />
        <div className="mode-toggle">
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "ask"}
              onChange={() => setMode("ask")}
            />
            Ask
          </label>
          <label>
            <input
              type="radio"
              name="mode"
              checked={mode === "search"}
              onChange={() => setMode("search")}
            />
            Search
          </label>
        </div>
        <button type="submit">Go</button>
      </form>

      <main>
        {fallback?.type === "summary" && (
          <SummaryCard
            title={fallback.title}
            extract={fallback.extract}
            thumbnail={fallback.thumbnail}
          />
        )}
        {fallback?.type === "search_results" && (
          <SearchResults hits={fallback.hits} onPick={onPickHit} />
        )}
        {fallback?.type === "no_results" && <div className="empty">{fallback.message}</div>}
        {(status || answer || error) && (
          <AnswerStream status={status} text={answer} sources={sources} error={error} />
        )}
      </main>
    </div>
  );
}
