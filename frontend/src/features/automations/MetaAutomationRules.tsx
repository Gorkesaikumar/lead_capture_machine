export default function MetaAutomationRules() {
  return <details className="my-5 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
    <summary className="cursor-pointer font-semibold text-slate-900">Messaging rules and Meta charges</summary>
    <div className="mt-3 space-y-2 leading-relaxed">
      <p>Our monthly run allowance is an application limit. Meta does not provide a universal monthly automation quota; account limits, quality controls and messaging windows still apply.</p>
      <p>Instagram automated replies require a customer message and an open 24-hour reply window. The Human Agent exception cannot be used for automated replies.</p>
      <p>WhatsApp free-form replies require an open 24-hour customer-service window. Outside it, an approved template is required. Meta may charge for delivered templates according to category, recipient market and volume tier.</p>
      <p>The ₹399 add-on covers the automation tool, not Meta or provider fees. Check the current official rate card before sending paid templates; this app does not estimate unverified per-message prices.</p>
      <p>One matching rule started for one incoming message counts as one run, including runs whose actions later fail. Multiple actions within that rule use one run. Drafts, previews, duplicates, non-matches and quota-blocked runs use none. No automatic overage charges.</p>
      <div className="flex flex-wrap gap-4 pt-2"><a className="underline" href="https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api" target="_blank" rel="noreferrer">Instagram messaging rules</a><a className="underline" href="https://business.whatsapp.com/products/platform-pricing" target="_blank" rel="noreferrer">Current WhatsApp pricing</a><a className="underline" href="https://developers.facebook.com/docs/whatsapp/messaging-limits" target="_blank" rel="noreferrer">WhatsApp account limits</a></div>
    </div>
  </details>;
}
