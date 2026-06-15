import { Link } from "react-router-dom";

const LOGINS = [
  { role: "Shopper", email: "demo@buildright.com", pass: "Demo1234!" },
  { role: "Manager", email: "manager@buildright.com", pass: "ManagerDemo1234!" },
  { role: "Staff", email: "staff@buildright.com", pass: "StaffDemo1234!" },
];

const STEPS: { title: string; prompt?: string; look: string }[] = [
  {
    title: "Grounded product search",
    prompt: "Do you have a cordless drill and how much is the cheapest one?",
    look: "Real product names + exact prices with SKUs — nothing invented. Prices come from the catalog, validated by a guardrail.",
  },
  {
    title: "Guardrail: apologize + suggest an alternative",
    prompt: "Do you sell a laser level?",
    look: "If it's not carried, the assistant apologizes and proactively offers the closest in-stock alternative — it never makes up a product or price.",
  },
  {
    title: "Policy answer with a citation (RAG)",
    prompt: "What's your return policy for power tools?",
    look: "An answer grounded in the knowledge base, cited as “Document › Section”. Ask something not in policy and it points you to customer service.",
  },
  {
    title: "Buying-guide knowledge (semantic search)",
    prompt: "What's the difference between an impact driver and a hammer drill?",
    look: "A grounded, cited buying-guide answer — semantic search over product knowledge, not a generic web answer.",
  },
  {
    title: "Conversational project planner",
    prompt: "I want to paint my bedroom, it's 12 by 10 feet with 8 foot walls. What do I need?",
    look: "A costed materials list (real SKUs, quantities, a subtotal) computed from the measurements, with an offer to add it all to the cart.",
  },
  {
    title: "Recommendations",
    prompt: "What goes well with a cordless drill?",
    look: "Cross-sell suggestions from real co-purchase data + content similarity.",
  },
  {
    title: "Multimodal — image & voice",
    look: "Use the 🖼️ button to find a product from a photo, and the 🎤 button to order by voice. Shortlisted items can be pushed to the storefront with one click.",
  },
  {
    title: "Manager analytics & AI Operations",
    look: "Log in as Manager → Dashboard. See inventory, profit, AI-attributed sales, and the AI Operations panel: agent cost, route mix (Haiku→Sonnet escalation), tool usage, guardrail rate, and customer-satisfaction scores.",
  },
];

function Copy({ text }: { text: string }) {
  return (
    <button
      onClick={() => navigator.clipboard?.writeText(text)}
      className="rounded border border-gray-300 px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100"
      title="Copy prompt"
    >
      Copy
    </button>
  );
}

export default function HowToTest() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-6 text-white sm:p-8">
        <h1 className="text-2xl font-bold sm:text-3xl">How to test BuildRight in 5 minutes</h1>
        <p className="mt-1 max-w-2xl text-sm opacity-90 sm:text-base">
          Open the chat (💬 bottom-right) and try the prompts below — each one shows a different capability.
          It's a sandbox: test data only, Stripe test mode, and it re-seeds on every deploy.
        </p>
      </div>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Demo logins</h2>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr><th className="px-4 py-2">Role</th><th className="px-4 py-2">Email</th><th className="px-4 py-2">Password</th></tr>
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
          Or shop + chat as a guest with no login. Admin is kept private for sandbox integrity.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Try these, in order</h2>
        <ol className="space-y-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="card p-4">
              <div className="flex items-start gap-3">
                <span className="badge mt-0.5 bg-brand-100 text-brand-700">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold">{s.title}</h3>
                  {s.prompt && (
                    <div className="mt-2 flex items-center gap-2">
                      <code className="min-w-0 flex-1 truncate rounded bg-gray-50 px-2 py-1 text-xs text-gray-700">
                        {s.prompt}
                      </code>
                      <Copy text={s.prompt} />
                    </div>
                  )}
                  <p className="mt-2 text-sm text-gray-600">
                    <span className="font-medium text-gray-500">What to look for: </span>{s.look}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="text-sm text-gray-500">
        Want the architecture + capabilities? See the <Link to="/about" className="text-brand-600 hover:underline">About page</Link>.
      </div>
    </div>
  );
}
