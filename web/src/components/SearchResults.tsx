import type { SearchHit } from "../api";

interface Props {
  hits: SearchHit[];
  onPick: (title: string) => void;
}

export function SearchResults({ hits, onPick }: Props) {
  return (
    <ul className="search-results">
      {hits.map((h) => (
        <li key={h.title}>
          <button onClick={() => onPick(h.title)}>{h.title}</button>
          <p dangerouslySetInnerHTML={{ __html: h.snippet }} />
        </li>
      ))}
    </ul>
  );
}
