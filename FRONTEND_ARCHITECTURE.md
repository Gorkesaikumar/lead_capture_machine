# Frontend Architecture & Discovery Audit

## 1. API Inventory

Based on an inspection of the Django REST Framework (DRF) backend routing (`config/urls.py` and application `urls.py`), the following endpoints are available under the `/api/v1/` prefix:

### Authentication & Accounts
- `POST /api/v1/auth/...` - Session/Token authentication endpoints.
- `GET/PUT /api/v1/accounts/...` - Admin account management.

### CRM & Operations
- `GET/POST/PUT/PATCH/DELETE /api/v1/leads/` - Core lead management.
- `GET/POST/PUT/PATCH/DELETE /api/v1/leads/triggers/` - Automation triggers for Meta webhooks.
- `GET/POST/PUT/PATCH/DELETE /api/v1/customers/` - Customer directory.
- `GET/POST/PUT/PATCH/DELETE /api/v1/conversations/` - Unified messaging view for IG/WhatsApp.

### Photography Services
- `GET/POST/PUT/PATCH/DELETE /api/v1/services/` - Base photography services.
- `GET/POST/PUT/PATCH/DELETE /api/v1/services/packages/` - Package configurations.

### Scheduling & Availability
- `GET /api/v1/scheduling/availability/` (and top-level `availability/`) - Computed availability slots.
- `GET/POST/PUT/PATCH/DELETE /api/v1/scheduling/weekly/` - Weekly repeating schedules.
- `GET/POST/PUT/PATCH/DELETE /api/v1/scheduling/special/` - Special date availability.
- `GET/POST/PUT/PATCH/DELETE /api/v1/scheduling/blocked-periods/` - Blocked times/dates.
- `GET/POST/PUT/PATCH/DELETE /api/v1/scheduling/holidays/` - Holiday closures.

### Bookings
- `GET/POST/PUT/PATCH/DELETE /api/v1/bookings/` - Admin booking management.
- `POST /api/v1/bookings/links/` - Generate a secure booking link to send to a customer.
- `GET /api/v1/bookings/links/<token>/` - Public endpoint to retrieve link details.
- `GET /api/v1/bookings/links/<token>/availability/` - Public endpoint to see available slots for the linked service.
- `POST /api/v1/bookings/links/<token>/confirm/` - Public endpoint to confirm the booking.

### System & Integrations
- `POST /api/v1/integrations/messages/send/` - Outbound messaging to IG/WhatsApp.
- Webhook targets: `webhooks/meta/instagram/`, `webhooks/meta/whatsapp/`.
- `GET /api/v1/notifications/` - Notification feeds.
- `GET /api/v1/analytics/` - Reporting and KPI data.
- `GET /api/v1/audit/` - System audit logs.
- Health checks: `/health/`, `/ping/`.

---

## 2. Page Inventory & Navigation Architecture

The Admin dashboard will be desktop-first (with mobile support) and feature a clean sidebar layout:

### Sidebar Navigation
1. **Overview**: Dashboard with key metrics and today/tomorrow's shoots.
2. **CRM**
   - **Leads**: Pipeline view of active inquiries.
   - **Conversations**: Chat interface to respond to IG/WA messages.
   - **Customers**: Directory of converted/past customers.
3. **Bookings**
   - **Calendar**: Visual calendar view of upcoming sessions.
   - **All Bookings**: Tabular view of bookings.
   - **Availability**: Manage weekly schedules, holidays, and blocks.
4. **Studio**
   - **Services & Packages**: Configure what customers can book.
5. **Automation & Integrations**
   - **Lead Triggers**: Configure regex/keyword rules to capture leads.
   - **Integrations**: Monitor Instagram and WhatsApp connection status.
6. **Insights**
   - **Analytics**: Reports on lead conversion and booking volume.

### Public Pages (Customer Facing)
- **Booking Flow**: A streamlined, mobile-optimized experience starting from the secure link, picking a slot, and confirming.

---

## 3. Frontend Folder Structure

```
src/
├── api/             # Centralized Axios/fetch instances, API clients
├── assets/          # Static images, global CSS (Tailwind entry)
├── components/      # Reusable UI components
│   ├── ui/          # shadcn/ui components (buttons, dialogs, etc.)
│   ├── layout/      # Sidebar, Header, PageShell
│   └── shared/      # Product-specific shared components (e.g. StatusBadge)
├── features/        # Feature-based domains (leads, bookings, services, etc.)
│   └── [feature]/
│       ├── components/
│       ├── hooks/
│       └── utils/
├── hooks/           # Global React hooks (e.g., useAuth)
├── lib/             # Utility functions, formatters (date-fns wrappers)
├── routes/          # React Router configuration
├── stores/          # Global client state (if needed, e.g. Zustand for UI toggles)
└── types/           # Global TypeScript definitions & API schemas
```

---

## 4. State & Query Strategy

- **Server State**: `TanStack Query (React Query) v5`. We will use consistent query keys (e.g., `['leads', 'list']`, `['bookings', 'detail', id]`).
- **Client State**: Minimal client state using standard React `useState`/`useReducer`.
- **Form State**: `React Hook Form` paired with `Zod` for typed schema validation.

---

## 5. Design System Strategy

### Theme & Colors
- **Premium Light Mode**: Deep white backgrounds (`#FFFFFF`) with subtle off-white muted surfaces (`#F9FAFB`).
- **Typography**: Inter (or equivalent modern sans-serif). Strong hierarchical contrast (dark text for headings, muted gray for secondary text).
- **Accents**: 
  - Instagram: Subtle purple/pink badges.
  - WhatsApp: Soft green badges.
  - Statuses: Soft semantic colors (Blue for New, Green for Booked, Amber for Pending, Red for Lost).

### Components & Spacing
- Use `shadcn/ui` and `Tailwind CSS`.
- Consistent padding scale. Cards will have restrained borders (`border-gray-200`) and extremely subtle shadows (`shadow-sm`), maintaining a flat, sophisticated SaaS aesthetic.
- Buttons will have explicit hierarchy (Primary, Secondary, Ghost, Destructive).

---

## 6. Authentication & Error Strategy

- Implement an `Axios` interceptor (or custom fetch wrapper) to automatically attach tokens and intercept `401 Unauthorized` errors to redirect to Login.
- Error handling:
  - `400/422`: Mapped to inline form validation errors.
  - `409` (Conflict): E.g., double booking. Surfaced via modal or clear alert informing the admin.
  - `500`: Generic "Something went wrong" subtle toast.
- **Loading States**: Use standard skeletons for layout, disabled buttons with spinners for mutations. Avoid full-screen blocking spinners.

---

## Conclusion
The architecture is set for a production-grade React application. The next phase involves setting up the Vite project, initializing Tailwind CSS and shadcn/ui, and building the foundational layouts based on this audit.
