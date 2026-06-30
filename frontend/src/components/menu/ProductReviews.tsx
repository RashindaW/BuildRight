import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BadgeCheck, Sparkles } from "lucide-react";
import { menuApi } from "../../lib/api/endpoints";
import { queryClient } from "../../lib/queryClient";
import { useToast } from "../../context/ToastProvider";
import { Stars, StarInput } from "../ui/Stars";
import { Skeleton } from "../ui/Skeleton";

export function ProductReviews({ slug }: { slug: string }) {
  const toast = useToast();
  const reviews = useQuery({ queryKey: ["reviews", slug], queryFn: () => menuApi.reviews(slug) });
  const summary = useQuery({ queryKey: ["review-summary", slug], queryFn: () => menuApi.reviewSummary(slug) });
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");

  const submit = useMutation({
    mutationFn: () =>
      menuApi.addReview(slug, { rating, comment: comment || undefined, author_name: name || undefined }),
    onSuccess: () => {
      toast("Thanks for your review!", "success");
      setRating(0);
      setComment("");
      setName("");
      queryClient.invalidateQueries({ queryKey: ["reviews", slug] });
      queryClient.invalidateQueries({ queryKey: ["review-summary", slug] });
      queryClient.invalidateQueries({ queryKey: ["menu-item", slug] });
    },
    onError: (e) => toast((e as Error).message, "error"),
  });

  const items = reviews.data?.items ?? [];
  const s = summary.data;

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold">
        Reviews {s && s.count > 0 && <span className="text-sm font-normal text-gray-500">({s.count})</span>}
      </h2>

      {s && s.count > 0 && (
        <div className="mb-4 flex gap-2 rounded-xl border border-brand-100 bg-brand-50/70 p-3 text-sm">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-brand-600" />
          <div>
            <div className="font-medium text-brand-800">What customers say</div>
            <p className="text-gray-700">{s.summary}</p>
            <div className="mt-1 flex items-center gap-2">
              {s.average != null && <Stars value={s.average} showValue size={13} />}
              <span className="text-xs text-gray-500">
                {s.positive} positive · {s.negative} critical
              </span>
            </div>
          </div>
        </div>
      )}

      {reviews.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">No reviews yet — be the first to review this product.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((r) => (
            <li key={r.id} className="card p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Stars value={r.rating} size={13} />
                  <span className="text-sm font-medium">{r.author_name}</span>
                  {r.verified_purchase && (
                    <span className="badge-success">
                      <BadgeCheck size={11} /> Verified
                    </span>
                  )}
                </div>
                <span className="whitespace-nowrap text-xs text-gray-400">
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </div>
              {r.comment && <p className="mt-1 text-sm text-gray-700">{r.comment}</p>}
            </li>
          ))}
        </ul>
      )}

      <form
        className="card mt-4 space-y-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (rating < 1) {
            toast("Please choose a star rating.", "error");
            return;
          }
          submit.mutate();
        }}
      >
        <div className="font-medium">Write a review</div>
        <StarInput value={rating} onChange={setRating} />
        <input
          className="input"
          placeholder="Your name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
        />
        <textarea
          className="input"
          placeholder="Share your experience (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          maxLength={2000}
        />
        <button className="btn-primary" disabled={submit.isPending}>
          {submit.isPending ? "Posting…" : "Post review"}
        </button>
      </form>
    </section>
  );
}
