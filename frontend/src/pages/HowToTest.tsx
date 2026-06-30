import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, BarChart3, Check, Copy as CopyIcon, CreditCard, FlaskConical,
  MessageCircle, Mic, Network, ShieldCheck, ShoppingBag,
} from "lucide-react";
import { Hero } from "../components/layout/Hero";
import { GROUP_ORDER, MISSIONS, type Mission } from "../components/howto/missions";

const LOGINS = [
  { role: "Shopper", email: "demo@buildright.com", pass: "Demo1234!" },
  { role: "Manager", email: "manager@buildright.com", pass: "ManagerDemo1234!" },
  { role: "Staff", email: "staff@buildright.com", pass: "StaffDemo1234!" },
];

const GROUP_ICON: Record<string, typeof ShoppingBag> = {
  "Shop as a guest": ShoppingBag,
  "Reviews & the recommendation graph": Network,
  "Chat with the AI assistant": MessageCircle,
  "Multimodal & memory": Mic,
  "Checkout & orders": CreditCard,
  "Manager intelligence (log in)": BarChart3,
  "Power features & access control": ShieldCheck,
};

/** A clean in-app path to deep-link to, or null if the route is an instruction. */
function linkTarget(route?: string): string | null {
  if (!route || !route.startsWith("/")) return null;
  const first = route.split(/\s/)[0];
  return /^\/[\w\-/]*$/.test(first) ? first : null;
}

function Copy({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1200);
      }}
      className="inline-flex shrink-0 items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-500 hover:bg-gray-100"
      title="Copy prompt"
    >
      {done ? <><Check size={12} /> Copied</> : <><CopyIcon size={12} /> Copy</>}
    </button>
  );
}

function MissionCard({ m, num }: { m: Mission; num: number }) {
  const target = linkTarget(m.route);
  return (
    <li className="card p-4">
      <div className="flex gap-3">
        <span className="badge-brand mt-0.5 shrink-0">{num}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h4 className="font-semibold text-gray-900">{m.title}</h4>
            {target && (
              <Link to={target} className="btn-soft btn-sm shrink-0">
                Try it <ArrowRight size={13} />
              </Link>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <span className="badge-neutral">{m.persona}</span>
            {m.route && <span className="font-mono text-xs text-gray-400">{m.route}</span>}
          </div>
          {m.prompt && (
            <div className="mt-2 flex items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded bg-gray-50 px-2 py-1 text-xs text-gray-700">
                {m.prompt}
              </code>
              <Copy text={m.prompt} />
            </div>
          )}
          <p className="mt-2 text-sm text-gray-600">
            <span className="font-medium text-gray-500">What to look for: </span>
            {m.lookFor}
          </p>
        </div>
      </div>
    </li>
  );
}

export default function HowToTest() {
  let counter = 0;
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Hero
        variant="test"
        eyebrow={<><FlaskConical size={13} /> Guided tour</>}
        title="Test every feature in about six minutes"
        subtitle="A guided lap, not a manual. Follow the missions top to bottom — start as a guest, push the assistant until it surprises you, dig into a product's reviews and recommendation graph, then log in as the manager to watch the machine's vitals. Tap any “Try it” to jump there; tap “Copy” to paste a prompt into the chat."
      />

      <section className="my-8">
        <h2 className="mb-3 text-lg font-semibold">Demo logins</h2>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="px-4 py-2">Role</th>
                <th className="px-4 py-2">Email</th>
                <th className="px-4 py-2">Password</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {LOGINS.map((l) => (
                <tr key={l.email}>
                  <td className="px-4 py-2 font-medium">{l.role}</td>
                  <td className="px-4 py-2 font-mono text-xs">{l.email}</td>
                  <td className="px-4 py-2 font-mono text-xs">{l.pass}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-400">
          Or shop + chat as a guest with no login. Admin access is kept private.
        </p>
      </section>

      {GROUP_ORDER.map((group) => {
        const items = MISSIONS.filter((m) => m.group === group);
        const Icon = GROUP_ICON[group] ?? ShoppingBag;
        return (
          <section key={group} className="mb-8">
            <div className="mb-3 flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white shadow-sm">
                <Icon size={17} />
              </span>
              <h2 className="text-lg font-semibold">{group}</h2>
              <span className="text-sm text-gray-400">({items.length})</span>
            </div>
            <ol className="space-y-3">
              {items.map((m) => {
                counter += 1;
                return <MissionCard key={m.title} m={m} num={counter} />;
              })}
            </ol>
          </section>
        );
      })}

      <div className="text-sm text-gray-500">
        Want the architecture &amp; how it's built? See the{" "}
        <Link to="/about" className="text-brand-600 hover:underline">About page</Link>.
      </div>
    </div>
  );
}
