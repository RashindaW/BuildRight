import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cartApi } from "../lib/api/endpoints";

export function useCart() {
  // Works for logged-in users AND anonymous guests (session-based cart).
  return useQuery({
    queryKey: ["cart"],
    queryFn: cartApi.get,
  });
}

export function useCartMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["cart"] });

  return {
    add: useMutation({
      mutationFn: (v: { id: string; qty?: number; options?: string[] }) =>
        cartApi.add(v.id, v.qty ?? 1, v.options ?? []),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: (v: { itemId: string; qty: number }) => cartApi.update(v.itemId, v.qty),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (itemId: string) => cartApi.remove(itemId),
      onSuccess: invalidate,
    }),
    clear: useMutation({ mutationFn: cartApi.clear, onSuccess: invalidate }),
  };
}
