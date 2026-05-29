import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cartApi } from "../lib/api/endpoints";
import { useAuth } from "../context/AuthProvider";

export function useCart() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["cart"],
    queryFn: cartApi.get,
    enabled: !!user,
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
