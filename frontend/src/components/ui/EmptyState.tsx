import type { ReactNode } from "react";

/** Consistent empty state: icon + title + copy + optional CTA. */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex animate-fade-in flex-col items-center justify-center rounded-xl2 border border-dashed border-gray-300 bg-white/60 px-6 py-14 text-center">
      {icon && (
        <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-gray-100 text-gray-400">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-gray-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
