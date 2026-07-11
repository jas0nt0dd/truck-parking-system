# Smart Truck Parking Management System (Beta)

Digital parking management system for a truck yard in India.  
Goal: Replace manual registers with a **mobile-first PWA** for gatekeepers and a transparent admin panel for owners.

> **Roles (Beta):**
> - Gatekeeper
> - Admin (Owner, plus additional admins created by root)

This document is the **master specification** for building the beta version. It covers architecture, database schema, backend APIs, frontend structure, and MSG91 WhatsApp integration.

---

## 1. High-Level Overview

### 1.1 Problem

Currently, the truck yard uses **manual registers** to track truck entries, exits, and payments. This is:

- Error-prone and slow
- Hard for the owner/admin to monitor
- Not transparent
- Difficult to audit

We want a **simple, fast, mobile-first system** where:

- Gatekeeper can:
  - Quickly register entries
  - Capture truck photos
  - Mark exits and payments
- Admin can:
  - View live parking status
  - Check history and reports
  - Control billing rules
  - Manage users (gatekeepers/admins)

---

### 1.2 Core Features (Beta)

- **Truck Entry (Gatekeeper)**
  - Entry should be completed in **≤20 seconds**
  - Fields:
    - Truck Number (required)
    - Driver Mobile (required)
    - Driver Name (optional)
    - Transport Company (optional)
    - Vehicle Type (optional)
    - Remarks (optional)
    - Entry Time (auto)
    - Entry Photo via phone camera (optional)
  - On save:
    - Truck status becomes “Inside”
    - Optional WhatsApp entry message via MSG91

- **Truck Exit (Gatekeeper)**
  - Search by:
    - Truck Number
    - Driver Mobile
  - Show:
    - Entry Time
    - Exit Time
    - Duration
    - Parking Charges (based on dynamic rules)
  - Payment:
    - Gatekeeper collects **cash / UPI manually**
    - Marks payment as paid in system
  - On mark paid:
    - Optional WhatsApp exit message via MSG91

- **Billing (Admin)**
  - Billing rules configurable from admin panel
  - Example (default):
    - First 12 Hours = ₹100
    - 12–24 Hours = ₹150
    - Additional Day = ₹100
  - **No code change** needed to update rules

- **Dashboard (Admin)**
  - Live stats:
    - Trucks currently parked
    - Today’s entries
    - Today’s exits
    - Today’s revenue
    - Pending payments
  - Live list of trucks inside:
    - Truck Number
    - Driver Mobile
    - Entry Time
    - Duration
    - Payment Status

- **Search & History (Admin)**
  - Search by:
    - Truck Number
    - Mobile Number
    - Date range
  - View complete visit history per truck

- **Reports (Admin)**
  - Filter for:
    - One day / week / month / custom range
  - Export options:
    - Excel (primary)
    - PDF (optional/secondary)

- **User Management (Admin)**
  - Root admin (owner) created initially
  - Admin can:
    - Add admins
    - Add gatekeepers
    - Disable users
    - Reset passwords

---

## 2. Tech Stack

### 2.1 Frontend

- **Framework:** Next.js 14+ (App Router) with TypeScript  
- **UI:** Tailwind CSS + shadcn/ui  
- **PWA:** Service worker, manifest, offline fallback  
- **Target:** Mobile-first (Android), but works on desktop browsers  

### 2.2 Backend

- **Framework:** FastAPI (Python 3.11+, async)  
- **Server:** Uvicorn + Gunicorn  
- **Auth:** JWT-based auth (access + refresh tokens)  
- **Password Hashing:** bcrypt  

### 2.3 Database

- **DB:** PostgreSQL (Supabase/Railway/other)  
- **ORM:** SQLAlchemy 2.0 (async)  
- **Migrations:** Alembic  

### 2.4 Messaging

- **WhatsApp:** MSG91 WhatsApp Business API  
  - Used for:
    - Truck entry notification
    - Truck exit + payment receipt  
  - Admin must configure MSG91 account, WhatsApp templates, and API credentials.

---

## 3. Backend Design (FastAPI)

### 3.1 Project Structure

```bash
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py        # Settings & environment variables
│   │   ├── security.py      # JWT, bcrypt
│   │   └── dependencies.py  # auth dependencies and role checks
│   ├── db/
│   │   ├── base.py          # Base = declarative_base()
│   │   ├── session.py       # async engine & session
│   │   └── migrations/      # Alembic migrations
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic models (input/output)
│   ├── routers/
│   │   ├── auth.py
│   │   ├── trucks.py
│   │   ├── sessions.py
│   │   ├── payments.py
│   │   ├── reports.py
│   │   ├── settings.py
│   │   └── users.py
│   ├── services/
│   │   ├── billing.py       # billing rules & calculation
│   │   ├── messaging.py     # MSG91 WhatsApp integration
│   │   └── exports.py       # Excel/PDF exports
│   └── utils/
│       ├── time.py          # time, timezone, duration
│       └── logging.py
└── tests/
```

---

### 3.2 Data Model

All primary keys are **UUID**. Times stored in UTC, converted to IST on frontend.

#### 3.2.1 Users

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum("admin", "gatekeeper", name="user_role"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
```

#### 3.2.2 Trucks

```python
class Truck(Base):
    __tablename__ = "trucks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    truck_number = Column(String, nullable=False, index=True)  # stored UPPER
    driver_name = Column(String)
    driver_mobile = Column(String, nullable=False, index=True)
    transport_company = Column(String)
    vehicle_type = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
```

#### 3.2.3 Parking Sessions

```python
class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    truck_id = Column(UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True))
    entry_photo_url = Column(String)
    exit_photo_url = Column(String)
    status = Column(Enum("inside", "exited", name="session_status"), default="inside", nullable=False)
    remarks = Column(Text)
    gatekeeper_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
```

#### 3.2.4 Billing Rules

```python
class BillingRule(Base):
    __tablename__ = "billing_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_name = Column(String, nullable=False)
    from_hours = Column(Numeric(10, 2), nullable=False)
    to_hours = Column(Numeric(10, 2))  # nullable for open-ended
    charge = Column(Numeric(10, 2), nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
```

#### 3.2.5 Payments (Manual)

```python
class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("parking_sessions.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_mode = Column(Enum("cash", "upi", "credit", name="payment_mode"), nullable=False)
    payment_status = Column(Enum("paid", "pending", "credit", name="payment_status"), nullable=False)
    paid_at = Column(DateTime(timezone=True))
    gatekeeper_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=func.now())
```

#### 3.2.6 Notifications (WhatsApp via MSG91)

```python
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("parking_sessions.id"))
    mobile = Column(String, nullable=False)
    channel = Column(Enum("whatsapp", name="notification_channel"), nullable=False)
    message_type = Column(Enum("entry", "exit", name="notification_type"), nullable=False)
    status = Column(Enum("pending", "sent", "failed", name="notification_status"), default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    last_attempted_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
```

#### 3.2.7 System Settings

```python
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    parking_name = Column(String)
    company_details = Column(JSON)
    logo_url = Column(String)
    msg91_authkey = Column(String)
    msg91_sender_id = Column(String)
    msg91_whatsapp_number = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
```

---

### 3.3 Auth & Roles

- `POST /auth/login`
  - Input: mobile + password
  - Output: `access_token`, `refresh_token`, user info
- `POST /auth/refresh`
  - Input: `refresh_token`
- Roles:
  - `admin`
  - `gatekeeper`
- Protect routes with dependencies:
  - `require_admin`
  - `require_gatekeeper_or_admin`

---

### 3.4 Key API Endpoints

#### 3.4.1 Sessions (Entry & Exit)

**POST `/sessions/entry`**

- Request body:
  - truck_number (string)
  - driver_mobile (string)
  - driver_name (optional)
  - transport_company (optional)
  - vehicle_type (optional)
  - remarks (optional)
  - entry_photo_url (optional)
- Logic:
  - Normalize `truck_number` to upper case
  - Find or create `Truck`
  - Create `ParkingSession` with:
    - `entry_time = now`
    - `status = "inside"`
    - `gatekeeper_id = current_user.id`
  - Optionally enqueue entry WhatsApp notification via MSG91
- Response:
  - Session + truck data

**POST `/sessions/{session_id}/exit`**

- Request body:
  - exit_photo_url (optional)
- Logic:
  - Set `exit_time = now`, `status = "exited"`
  - Compute duration in hours
  - Call billing engine to calculate charge
  - Create `Payment` record with:
    - `payment_status = "pending"`
  - Response includes:
    - session data
    - `amount_due`
    - billing breakdown

---

#### 3.4.2 Payments

**POST `/payments/{session_id}/mark-paid`**

- Request body:
  - `payment_mode` (`cash`, `upi`, `credit`)
  - `amount` (optional; default from billing engine)
- Logic:
  - Update payment record:
    - `payment_status = "paid"`
    - `paid_at = now`
    - `gatekeeper_id = current_user.id`
  - Trigger exit WhatsApp notification (via MSG91)
- Response:
  - final session + payment info

---

#### 3.4.3 Search & History

**GET `/sessions/search`**

- Query params:
  - `q` (truck number or mobile)
  - `status` (optional: `inside` or `exited`)
- Returns:
  - List of matching sessions (with truck details)

**GET `/sessions/history`**

- Query:
  - `truck_number` (optional)
  - `driver_mobile` (optional)
  - `from_date`, `to_date` (optional)
  - `page`, `page_size` (pagination)
- Returns:
  - Paginated list of sessions (history)

---

#### 3.4.4 Dashboard & Reports

**GET `/dashboard/summary` (admin)**

- Returns:
  - `trucks_inside`
  - `entries_today`
  - `exits_today`
  - `revenue_today`
  - `pending_payments`

**GET `/dashboard/live`**

- Returns live list of sessions with:
  - truck_number
  - driver_mobile
  - entry_time
  - duration
  - payment_status

**GET `/reports/export`**

- Query:
  - `from_date`
  - `to_date`
  - `format` = `excel` (beta) / `pdf` (optional)
- Logic:
  - Generate report using sessions + payments
  - For Excel: use `openpyxl`
  - Return file download

---

#### 3.4.5 Billing Rules (Admin)

**GET `/billing/rules`**  
**POST `/billing/rules`**  
**PUT `/billing/rules/{id}`**  
**DELETE `/billing/rules/{id}`**

- Admin can manage billing rules without changing code.

---

#### 3.4.6 Users (Admin)

**GET `/users`**  
**POST `/users`** – create admin/gatekeeper  
**PUT `/users/{id}`** – update  
**PATCH `/users/{id}/status`** – activate/deactivate  
**POST `/users/{id}/reset-password`**

Root admin cannot be deleted.

---

### 3.5 Billing Engine Logic

**Input:**
- `duration_hours` (float)
- list of active `BillingRule` from DB

**Algorithm (simplified):**

```python
def calculate_charge(duration_hours: float, rules: list[BillingRule]):
    total = Decimal("0.00")
    breakdown = []

    for rule in sorted(rules, key=lambda r: r.priority):
        if rule.to_hours is not None:
            if rule.from_hours < duration_hours <= rule.to_hours:
                total += rule.charge
                breakdown.append((rule.rule_name, rule.charge))
        else:
            # open-ended rule e.g., "Additional Day"
            if duration_hours > rule.from_hours:
                extra_hours = duration_hours - rule.from_hours
                days = math.ceil(extra_hours / 24)
                extra = rule.charge * days
                total += extra
                breakdown.append((rule.rule_name, extra))

    return total, breakdown
```

---

### 3.6 MSG91 WhatsApp Integration

MSG91 provides a WhatsApp Business API for sending template-based messages [web:54][web:7][web:60].

**Steps:**

1. Admin configures:
   - MSG91 `authkey`
   - WhatsApp sender number
   - Template IDs
2. Backend service:
   - `MSG91WhatsAppProvider`:
     - `send_entry_message(session, truck)`
     - `send_exit_message(session, truck, payment)`
3. For each message:
   - Prepare template variables:
     - Truck number
     - Entry time
     - Exit time
     - Duration
     - Amount paid
     - Payment mode
   - Call MSG91 API via HTTP POST [web:7][web:56]
   - Store result in `notifications` table

---

## 4. Frontend Design (Next.js)

### 4.1 Project Structure

```bash
frontend/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── (gatekeeper)/
│   │   ├── entry/page.tsx
│   │   ├── exit/page.tsx
│   │   └── history/page.tsx   # optional
│   ├── (admin)/
│   │   ├── dashboard/page.tsx
│   │   ├── sessions/page.tsx
│   │   ├── billing/page.tsx
│   │   ├── users/page.tsx
│   │   └── reports/page.tsx
│   └── layout.tsx
├── components/
│   ├── TruckEntryForm.tsx
│   ├── TruckExitSearch.tsx
│   ├── TruckExitDetails.tsx
│   ├── LiveParkingTable.tsx
│   ├── DashboardCards.tsx
│   ├── BillingRuleForm.tsx
│   └── UserForm.tsx
├── lib/
│   ├── api.ts                # axios instance, interceptors
│   ├── auth.ts               # token storage, refresh logic
│   └── utils.ts              # helpers (format time, etc.)
└── public/
    └── manifest.json         # PWA config
```

---

### 4.2 Authentication Flow

- On login:
  - Call `/auth/login`
  - Store `access_token` (and optionally `refresh_token`)
  - Redirect based on role:
    - `gatekeeper` → `/entry`
    - `admin` → `/admin/dashboard`
- Use Axios interceptors in `lib/api.ts`:
  - Attach `Authorization: Bearer <token>`
  - On 401, try refreshing token (optional in beta)

---

### 4.3 Gatekeeper Screens

#### 4.3.1 Entry Screen

- **TruckEntryForm**:
  - Inputs:
    - Truck Number (uppercase, validated)
    - Driver Mobile
    - Driver Name (optional)
    - Company (optional)
    - Vehicle Type (optional)
    - Remarks
  - Photo:
    - Capture via `<input type="file" accept="image/*" capture="environment" />`
  - Submit:
    - Large full-width "Save Entry" button
    - After success:
      - Show success state (green screen)
      - Clear form in 2–3 seconds
  - Performance:
    - Aim for minimal fields required
    - Ensure form works on mid-range Android quickly

#### 4.3.2 Exit Screen

- Search bar:
  - Input: truck number or mobile
  - Call `/sessions/search?q=`
- Results:
  - Show list of active sessions
- On selecting session:
  - Show:
    - Truck number
    - Driver mobile
    - Entry time
    - Current duration
    - Calculated amount from backend
  - Payment:
    - Buttons: `Cash`, `UPI`, `Credit`
  - Button:
    - "Mark as Paid & Exit"
    - Calls `/payments/{session_id}/mark-paid`
  - After success:
    - Show summary
    - Navigate back to search or entry

---

### 4.4 Admin Screens

#### 4.4.1 Dashboard

- **DashboardCards**:
  - Trucks inside
  - Today’s entries
  - Today’s exits
  - Today’s revenue
  - Pending payments
- **LiveParkingTable**:
  - Truck number
  - Driver mobile
  - Entry time
  - Duration
  - Payment status
- Auto-refresh using SWR/React Query with interval (e.g., 30s)

#### 4.4.2 Sessions/History

- Filters:
  - Truck number
  - Mobile
  - Date range
- Table:
  - All sessions matching filters
  - Pagination

#### 4.4.3 Billing Rules

- Table of rules:
  - Rule name
  - From hours
  - To hours
  - Charge
  - Priority
  - Active toggle
- Add/Edit dialog (BillingRuleForm)

#### 4.4.4 Users

- List users:
  - Name, role, status
- Add user:
  - Name, mobile, role, temporary password
- Enable/disable
- Reset password

#### 4.4.5 Reports

- Date range selector
- Filter by truck number/mobile (optional)
- Table view
- Export buttons:
  - "Export Excel"
  - "Export PDF" (optional)

---

### 4.5 PWA Configuration

**`public/manifest.json`**

```json
{
  "name": "Truck Parking Manager",
  "short_name": "TruckPark",
  "theme_color": "#1a1a2e",
  "background_color": "#ffffff",
  "display": "standalone",
  "scope": "/",
  "start_url": "/",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

Use a service worker (via next-pwa or custom) to:

- Cache static assets
- Cache basic API responses where possible
- Support offline entry caching (future improvement)

---

## 5. Development Plan

### 5.1 Phase 1 — Backend Skeleton

- Setup FastAPI project
- Configure DB, models, migrations
- Implement auth, users
- Implement sessions entry/exit
- Implement basic billing engine

### 5.2 Phase 2 — Gatekeeper Frontend

- Implement login
- Implement entry screen
- Implement exit search + mark-paid flow

### 5.3 Phase 3 — Admin Frontend

- Dashboard cards + live table
- Billing rules UI
- Users management
- History sessions table

### 5.4 Phase 4 — Reports & Export

- History filters
- Excel export API + button

### 5.5 Phase 5 — MSG91 Integration (WhatsApp)

- Setup messaging service in backend
- Integrate entry + exit notification triggers
- Test templates with sample messages

---

## 6. Future Enhancements (Post-Beta)

- Multi-yard (add `yard_id` everywhere)
- ANPR integration
- Online payment gateway (UPI/card)
- GPS logging
- Slot-based allocation once the yard is structured
- Better analytics & dashboards

---

## 7. Notes for Developers

- Keep code modular: services for billing, messaging, exports.
- Never calculate final price on frontend; always rely on backend billing engine.
- Respect WhatsApp template rules and MSG91 requirements.
- Always log:
  - who created entry
  - who processed exit
  - who marked payment
- Keep the gatekeeper UI **fast and minimal**; admin UI can be more detailed.

---

This `README.md` defines the entire beta system.  
Use it as the base in Claude to generate:

- Backend code (FastAPI models, routers, services)
- Frontend pages and components
- Integration with MSG91 for WhatsApp notifications.