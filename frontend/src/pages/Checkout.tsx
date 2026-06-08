import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import type { Stripe } from "@stripe/stripe-js";
import { useQueryClient } from "@tanstack/react-query";
import { useCart } from "../hooks/useCart";
import { paymentsApi } from "../lib/api/endpoints";
import { formatPrice } from "../lib/format";
import { useToast } from "../context/ToastProvider";

// ---- Inner payment form (must be inside <Elements>) ---------------------

function PaymentForm({
  orderId,
  onPaid,
}: {
  orderId: string;
  onPaid: (orderId: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const toast = useToast();
  const [paying, setPaying] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setPaying(true);
    try {
      const { error } = await stripe.confirmPayment({
        elements,
        redirect: "if_required",
      });
      if (error) {
        toast(error.message ?? "Payment failed", "error");
        return;
      }
      // Payment confirmed client-side; re-verify server-side (no tunnel needed)
      const result = await paymentsApi.confirm(orderId);
      if (result.payment_status === "paid") {
        onPaid(orderId);
      } else {
        toast("Payment could not be confirmed. Please contact support.", "error");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Something went wrong", "error");
    } finally {
      setPaying(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      <button className="btn-primary w-full" type="submit" disabled={paying || !stripe || !elements}>
        {paying ? "Processing…" : "Pay now"}
      </button>
      <p className="text-center text-xs text-gray-400">
        Test card: 4242 4242 4242 4242 · any future date · any CVC
      </p>
    </form>
  );
}

// ---- Main checkout component -------------------------------------------

type Step = "cart" | "payment";

interface IntentState {
  clientSecret: string;
  orderId: string;
  stripePromise: Promise<Stripe | null>;
}

export default function Checkout() {
  const { data: cart } = useCart();
  const nav = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");
  const [step, setStep] = useState<Step>("cart");
  const [intentState, setIntentState] = useState<IntentState | null>(null);
  const [loading, setLoading] = useState(false);

  const proceedToPayment = async () => {
    setLoading(true);
    try {
      const { client_secret, order_id, publishable_key } = await paymentsApi.createIntent(
        notes || undefined
      );
      const { loadStripe } = await import("@stripe/stripe-js");
      setIntentState({
        clientSecret: client_secret,
        orderId: order_id,
        stripePromise: loadStripe(publishable_key),
      });
      setStep("payment");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Something went wrong", "error");
    } finally {
      setLoading(false);
    }
  };

  const handlePaid = (orderId: string) => {
    qc.invalidateQueries({ queryKey: ["cart"] });
    qc.invalidateQueries({ queryKey: ["orders"] });
    nav(`/order/${orderId}`);
  };

  if (!cart || cart.items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p className="text-gray-500">Your cart is empty.</p>
        <button className="btn-primary mt-4" onClick={() => nav("/")}>
          Browse products
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Checkout</h1>

      {/* Order summary — always visible */}
      <div className="card p-4 mb-4">
        <ul className="divide-y">
          {cart.items.map((it) => (
            <li key={it.id} className="flex justify-between py-2">
              <span>
                {it.quantity} × {it.name}
              </span>
              <span>{formatPrice(it.line_total_cents)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex justify-between border-t pt-3 text-lg font-semibold">
          <span>Total</span>
          <span>{formatPrice(cart.subtotal_cents)}</span>
        </div>
      </div>

      {step === "cart" && (
        <>
          <label className="mt-4 block text-sm font-medium">
            Order notes (optional)
            <textarea
              className="mt-1 w-full rounded-lg border border-gray-300 p-2"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={500}
            />
          </label>
          <button
            className="btn-primary mt-4 w-full"
            onClick={proceedToPayment}
            disabled={loading}
          >
            {loading
              ? "Preparing payment…"
              : `Proceed to payment · ${formatPrice(cart.subtotal_cents)}`}
          </button>
        </>
      )}

      {step === "payment" && intentState && (
        <Elements
          stripe={intentState.stripePromise}
          options={{ clientSecret: intentState.clientSecret }}
        >
          <PaymentForm orderId={intentState.orderId} onPaid={handlePaid} />
        </Elements>
      )}
    </div>
  );
}
