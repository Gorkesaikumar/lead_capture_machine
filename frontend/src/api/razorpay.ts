type CheckoutResult = { razorpay_order_id?: string; razorpay_subscription_id?: string; razorpay_payment_id: string; razorpay_signature: string };
export type CheckoutOrder = { key: string; order_id?: string; subscription_id?: string; amount: number; currency: string; description: string };
type CheckoutOptions = Partial<CheckoutOrder> & { name: string; image: string; handler: (result: CheckoutResult) => void; modal: { ondismiss: () => void }; retry: { enabled: boolean } };
declare global {
  interface Window { Razorpay?: new (options: CheckoutOptions) => { open: () => void; on: (event: string, handler: (event: { error?: { description?: string } }) => void) => void } }
}
let loading: Promise<void> | undefined;

export async function openPaymentCheckout(order: CheckoutOrder): Promise<CheckoutResult> {
  if (!window.Razorpay) {
    loading ||= new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      const timeout = window.setTimeout(() => { script.remove(); reject(new Error("Payment checkout timed out. Please try again.")); }, 20000);
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => { clearTimeout(timeout); resolve(); };
      script.onerror = () => { clearTimeout(timeout); script.remove(); reject(new Error("Payment checkout could not load. Please try again.")); };
      document.head.appendChild(script);
    }).catch(error => { loading = undefined; throw error; });
    await loading;
  }
  if (!window.Razorpay) throw new Error("Payment checkout is unavailable.");
  const Checkout = window.Razorpay;
  return new Promise((resolve, reject) => {
    let failure: string | undefined;
    const checkout = new Checkout({ key: order.key,
      ...(order.subscription_id ? { subscription_id: order.subscription_id } : { order_id: order.order_id, amount: order.amount, currency: order.currency }),
      description: order.description, name: "Nextora", image: `${window.location.origin}/lead.png`, handler: resolve,
      retry: { enabled: true },
      modal: { ondismiss: () => reject(new Error(failure || "Checkout closed. Check payment status before trying again.")) },
    });
    checkout.on("payment.failed", event => { failure = event.error?.description || "Payment failed. You can retry securely in checkout."; });
    checkout.open();
  });
}
