interface Props {
  title: string;
  extract: string;
  thumbnail: string | null;
}

export function SummaryCard({ title, extract, thumbnail }: Props) {
  return (
    <div className="summary-card">
      {thumbnail && <img src={thumbnail} alt="" />}
      <h2>{title}</h2>
      <p>{extract}</p>
    </div>
  );
}
