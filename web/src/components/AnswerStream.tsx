interface Props {
  status: string;
  text: string;
  sources: string[];
  error: string | null;
}

export function AnswerStream({ status, text, sources, error }: Props) {
  if (error) return <div className="answer error">Error: {error}</div>;
  return (
    <div className="answer">
      <div className="answer-status">{status}</div>
      <div className="answer-text">{text}</div>
      {sources.length > 0 && (
        <div className="answer-sources">
          <strong>Sources:</strong> {sources.join(", ")}
        </div>
      )}
    </div>
  );
}
