export function formatCurrencyTotals(totals?: Record<string, string>): string {
  if (!totals) return "Unavailable";
  const values = Object.entries(totals);
  if (!values.length) return "No payments recorded";
  return values.map(([currency, amount]) => `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`).join(" / ");
}
