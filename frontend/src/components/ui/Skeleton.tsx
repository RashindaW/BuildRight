/** Shimmering placeholder block. Compose into card/list skeletons. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

/** A product-card-shaped skeleton for grid loading states. */
export function SkeletonCard() {
  return (
    <div className="card overflow-hidden">
      <Skeleton className="aspect-[4/3] w-full rounded-none" />
      <div className="space-y-2 p-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="mt-3 h-9 w-full" />
      </div>
    </div>
  );
}
