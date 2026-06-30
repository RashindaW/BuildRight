import { Link } from "react-router-dom";
import type { RecGraph } from "../../types";

/** Lightweight, dependency-free radial visualization of the GNN recommendation
 * neighbourhood: the anchor at the centre, top graph-neighbours around it, edge
 * thickness + node size proportional to graph similarity. */
export function GraphViz({ data, size = 360 }: { data: RecGraph; size?: number }) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.34;
  const n = Math.max(1, data.neighbors.length);
  const maxScore = Math.max(0.0001, ...data.neighbors.map((x) => x.score ?? 0));
  const trunc = (s: string, len: number) => (s.length > len ? s.slice(0, len - 1) + "…" : s);

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full" role="img" aria-label="Recommendation graph">
      {data.neighbors.map((nb, i) => {
        const a = (i / n) * 2 * Math.PI - Math.PI / 2;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        const w = 1 + 4 * ((nb.score ?? 0) / maxScore);
        return <line key={`e${i}`} x1={cx} y1={cy} x2={x} y2={y} stroke="#cbd5e1" strokeWidth={w} />;
      })}

      {data.neighbors.map((nb, i) => {
        const a = (i / n) * 2 * Math.PI - Math.PI / 2;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        const nodeR = 6 + 9 * ((nb.score ?? 0) / maxScore);
        const right = Math.cos(a) >= 0;
        return (
          <Link key={nb.slug} to={`/item/${nb.slug}`}>
            <circle cx={x} cy={y} r={nodeR} fill="#bfdbfe" stroke="#3b82f6" strokeWidth={1.5} />
            <text
              x={x + (right ? nodeR + 4 : -(nodeR + 4))}
              y={y + 3}
              fontSize="9"
              textAnchor={right ? "start" : "end"}
              fill="#334155"
            >
              {trunc(nb.name, 16)}
            </text>
          </Link>
        );
      })}

      <circle cx={cx} cy={cy} r={15} fill="#1d4ed8" />
      <text x={cx} y={cy + 30} fontSize="10" fontWeight={700} textAnchor="middle" fill="#1e293b">
        {trunc(data.anchor.name, 24)}
      </text>
    </svg>
  );
}
