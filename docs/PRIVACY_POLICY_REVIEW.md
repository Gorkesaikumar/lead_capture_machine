# Privacy policy implementation review

Prepared September 5, 2026. Operator: Nextora Creations. Confirmed privacy and data-deletion contact: **support@nextoracreations.co.in**.

## Public route and deployment status

- Route: `/privacy-policy` (also supports a trailing slash).
- Canonical production URL: https://studio.nextoracreations.co.in/privacy-policy
- Local preview: http://localhost:5173/privacy-policy
- The route sits outside authentication and realtime providers, including when an expired login token is present. It makes no authenticated API or WebSocket requests.
- The build generates `frontend/dist/privacy-policy/index.html` with the complete policy, title, description, canonical URL and social metadata. Crawlers and browsers without JavaScript receive meaningful policy content.
- No production deployment or infrastructure mutation was performed. A read-only request to the production URL returned HTTP 200, but its existing HTML did not contain the new policy heading. Production publication and a live content check remain outstanding; the existing 200 alone is not evidence that the policy is published.

## Files changed for this task

| File | Change |
| --- | --- |
| `frontend/src/features/legal/privacy-content.ts` | Policy text, date, canonical URL and confirmed contact. |
| `frontend/src/features/legal/PrivacyPolicy.tsx` | Responsive public page, table of contents, contact/deletion links and client-side metadata cleanup. |
| `frontend/src/features/legal/privacy.css` | Scoped legal-page accessibility and print styles. |
| `frontend/src/features/legal/privacy-render.tsx` | Server-rendering entry point using the same page component. |
| `frontend/scripts/prerender-privacy.mjs` | Build-time generation of complete static legal HTML. |
| `frontend/package.json` | Runs policy prerendering after the existing TypeScript/Vite build. |
| `frontend/src/App.tsx` | Public route outside the existing authenticated application providers. |
| `frontend/src/features/marketing/components/Navbar.tsx` | Reusable legal-header variant with existing branding and home navigation. |
| `frontend/src/features/marketing/components/Footer.tsx` | Legal-footer variant and working homepage Privacy Policy link. |
| `frontend/nginx.conf` | Exact public locations serving the generated policy for direct navigation and refresh. |
| `frontend/tests/privacy-policy.cjs` | Browser, routing, metadata, no-JavaScript and public-access regression checks. |
| `docs/PRIVACY_POLICY_REVIEW.md` | This review record. |

Other changes present in the working tree belong to separate work and are not part of this policy implementation.

## Content implemented

1. Introduction and operator/business responsibilities.
2. Information collected, including account, workspace, customer, conversation, billing and technical records.
3. Meta/Instagram authorization and the purposes of `instagram_business_basic` and `instagram_business_manage_messages`; no Instagram password collection.
4. Meta webhook data.
5. Authorization/access tokens.
6. Customer messages, leads and business-configured automation.
7. Purposes for using information.
8. Sharing and service providers.
9. Security controls supported by the application.
10. Retention without invented fixed periods.
11. Data Deletion and User Requests, including email instructions, revocation and configured Meta callbacks.
12. Third-party services and processing locations.
13. Actual cookies and browser storage, including authentication/workspace storage and Google Fonts disclosure in the third-party section.
14. Children.
15. Rights subject to applicable jurisdiction.
16. Policy changes.
17. Confirmed privacy contact.

The text was checked against the existing authentication storage, encrypted integration credentials, workspace authorization, billing integration and Meta deauthorization/deletion code. It does not invent a postal address, DPO, registration number, fixed retention schedule, data residency commitment or standalone deletion page. General notice-coverage reference: [ICO privacy information guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/).

## Nginx and routing

The frontend Nginx config serves `/privacy-policy/index.html` for the exact paths `/privacy-policy` and `/privacy-policy/`, returning 404 if a build omits the required document. Existing SPA fallback and asset handling remain in place. The existing production frontend Dockerfile copies the complete build output, so the generated policy is included automatically.

The outer reverse proxy's `/api/` and `/ws/` routing was inspected and did not require changes. No backend routes, schemas, OAuth handlers or webhook handlers were changed for this task.

## Verification results

- `npm run build`: passed, including TypeScript compilation, Vite bundling and privacy HTML generation. Vite retains its existing large-chunk warning.
- `node tests/privacy-policy.cjs`: passed against the Vite development server.
- `V4_PRIVACY_URL=http://127.0.0.1:5186 V4_PRIVACY_STATIC=1 node tests/privacy-policy.cjs`: passed against a temporary local Nginx container using the actual frontend Nginx configuration and production build output. Set these environment variables using the syntax of your shell.
- Browser coverage: fresh desktop/mobile contexts, expired authentication, direct navigation, refresh, contact/section anchors, homepage navigation and metadata cleanup, logo loading, no horizontal overflow, no authenticated requests or WebSockets, and no page/console errors.
- Static coverage: HTTP 200 with and without trailing slash, complete policy with JavaScript disabled, metadata, permission names, contact information and no placeholder secret markers.
- `node tests/dashboard-access.cjs`: passed the existing dashboard/admin access regression checks.
- `node tests/login-errors.cjs`: passed the existing login error and visibility regression checks.
- `docker exec nextora-privacy-review nginx -t`: passed for the temporary local review container.
- Built HTML/JS/CSS scan against configured long secret values: zero matches. No secret values were printed.
- `git -c core.safecrlf=false diff --check`: passed.
- Desktop/mobile screenshots were visually reviewed. Test screenshots are written under `frontend/test-results/privacy-policy/`.

## Remaining items

No missing business-contact TODO remains. The supplied support email is used throughout the policy. Production remains unchanged as requested; after a reviewed deployment, verify the canonical HTTPS URL returns the new policy content to an unauthenticated browser and a crawler.
