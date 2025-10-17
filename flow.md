## 🧭 PHASE 1 — CORE BACKEND FOUNDATION

### 🧱 TASK GROUP 1: Environment & Core Setup

**Goal:** Establish FastAPI base, config, and Supabase connection.

| Step | Task                           | File(s)                   | Description                                                                 |
| ---- | ------------------------------ | ------------------------- | --------------------------------------------------------------------------- |
| 1.1  | Create project scaffold        | `backend/app` structure   | Create folders: `core`, `routers`, `schemas`, `services`, `utils`, `tests`. |
| 1.2  | Setup `.env` and config loader | `core/config.py`          | Load `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`, etc.                     |
| 1.3  | Initialize Supabase client     | `core/supabase_client.py` | Create reusable `get_supabase()` function.                                  |
| 1.4  | Setup FastAPI app              | `main.py`                 | Add CORS, router registration, exception handling.                          |
| 1.5  | Setup logging utility          | `utils/logger.py`         | Centralized async logger for audit logs.                                    |

---

### 🧩 TASK GROUP 2: Authentication & Role Middleware

**Goal:** Handle JWT decoding and RBAC enforcement.

| Step | Task                              | File(s)                                                           | Description                                      |
| ---- | --------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------ |
| 2.1  | Implement Supabase JWT validation | `core/auth.py`                                                    | Decode JWT and fetch user from Supabase.         |
| 2.2  | Create role guard dependency      | `core/role_guard.py`                                              | Validate that user role matches allowed roles.   |
| 2.3  | Add `/auth/validate` route        | `routers/users.py`                                                | Simple endpoint to verify token and return role. |
| 2.4  | Integrate role guard              | `@router.post(..., dependencies=[Depends(validate_role([...]))])` | Restrict access per role.                        |

---

## 💳 PHASE 2 — BILLING, SALES & CUSTOMER MODULE

### 💼 TASK GROUP 3: Billing Core Models

**Goal:** Implement the billing data layer.

| Step | Task                       | File(s)                       | Description                                                                                                |
| ---- | -------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 3.1  | Define schemas             | `schemas/billing.py`          | Define Pydantic models: `Quotation`, `SalesOrder`, `Invoice`, `Payment`, `Customer`, `LoyaltyTransaction`. |
| 3.2  | Implement billing services | `services/billing_service.py` | CRUD logic: quotation → order → invoice transitions.                                                       |
| 3.3  | Add PDF generator utility  | `utils/pdf_generator.py`      | Generate invoice PDFs via `reportlab`.                                                                     |
| 3.4  | Build billing routes       | `routers/billing.py`          | Expose `/billing/quotation`, `/billing/order`, `/billing/invoice` endpoints.                               |
| 3.5  | Add customer management    | `routers/users.py`            | CRUD for customer data + loyalty tracking.                                                                 |

**Functionality Flow:**

```

Quotation → SalesOrder → Invoice
↓           ↓           ↓
Approve     Convert     Generate PDF & Payment Tracking

```

**Advanced Features:**
- GST auto-calculation  
- Partial payment tracking  
- Loyalty points and customer history  

---

## 🏷️ PHASE 3 — INVENTORY & PRODUCT MANAGEMENT

### 📦 TASK GROUP 4: Inventory Core Models

**Goal:** Manage stock, suppliers, variants, and showroom/warehouse data.

| Step | Task                            | File(s)                         | Description                                                                                 |
| ---- | ------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------- |
| 4.1  | Define schemas                  | `schemas/inventory.py`          | `Product`, `Variant`, `Stock`, `Supplier`, `GRN`, `StockTransfer`, `Warranty`, `Complaint`. |
| 4.2  | Implement inventory services    | `services/inventory_service.py` | Handle CRUD + stock adjustment + transfers.                                                 |
| 4.3  | Create inventory routes         | `routers/inventory.py`          | `/inventory/products`, `/inventory/stock`, `/inventory/transfer`.                           |
| 4.4  | Add supplier mapping & GRN flow | `procurement_service.py`        | Link products → suppliers → purchase orders.                                                |
| 4.5  | Add real-time stock sync        | via Supabase Realtime           | Auto-update stock across branches.                                                          |

**Key Features:**
- Item-level & Set-level tracking  
- Material & variant management  
- Showroom vs Warehouse segregation  
- Low stock alerts (threshold-based)  
- QR/barcode generation for labels  

---

## 🧾 PHASE 4 — PROCUREMENT & SUPPLIER MANAGEMENT

### 🚚 TASK GROUP 5: Procurement Module

**Goal:** Manage purchase orders and vendor performance.

| Step | Task                       | File(s)                           | Description                                           |
| ---- | -------------------------- | --------------------------------- | ----------------------------------------------------- |
| 5.1  | Define procurement schemas | `schemas/procurement.py`          | `PurchaseOrder`, `PurchaseItem`, `VendorRating`.      |
| 5.2  | Implement services         | `services/procurement_service.py` | Handle PO lifecycle: Request → Approve → GRN → Close. |
| 5.3  | Create routes              | `routers/procurement.py`          | Endpoints for PO management.                          |
| 5.4  | Vendor analytics           | `report_service.py`               | Track vendor delivery quality & punctuality.          |

---

## 📊 PHASE 5 — REPORTS & ANALYTICS

### 📈 TASK GROUP 6: Reporting & Insights

**Goal:** Generate analytical and financial summaries.

| Step | Task                     | File(s)                      | Description                                                |
| ---- | ------------------------ | ---------------------------- | ---------------------------------------------------------- |
| 6.1  | Create reporting schemas | `schemas/reports.py`         | Response models for reports.                               |
| 6.2  | Implement report service | `services/report_service.py` | Generate aggregated SQL queries and insights.              |
| 6.3  | Add report routes        | `routers/reports.py`         | `/reports/sales`, `/reports/inventory`, `/reports/profit`. |
| 6.4  | PDF/Excel export utility | `utils/pdf_generator.py`     | Add support for summary export.                            |

**Reports:**
- Stock summary & movement  
- Fast/slow movers  
- Profit per product/category  
- Outstanding payments  
- Customer & vendor analysis  

---

## 🧑‍💼 PHASE 6 — USER MANAGEMENT & ROLE ADMIN

### 🔐 TASK GROUP 7: User & Role Admin

**Goal:** Centralize user and role CRUD + permissions.

| Step | Task                  | File(s)                 | Description                        |
| ---- | --------------------- | ----------------------- | ---------------------------------- |
| 7.1  | Define user schema    | `schemas/users.py`      | Include `role`, `email`, `status`. |
| 7.2  | Add admin route       | `routers/users.py`      | `/admin/users` CRUD.               |
| 7.3  | Role-based dashboards | (Later phase, optional) | Provide metrics per role.          |
| 7.4  | Action logs           | `utils/logger.py`       | Track modifications by user ID.    |

**Roles:**
- `Admin` → Full access  
- `Cashier` → Billing + Payments  
- `Sales Executive` → Quotation + Orders  
- `Inventory Manager` → Stock + Procurement  

---

## ⚙️ PHASE 7 — SYSTEM ENHANCEMENTS & PREMIUM FEATURES

### 🌐 TASK GROUP 8: System-Level Add-ons

**Goal:** Enterprise-ready enhancements.

| Step | Task                        | File(s)             | Description                                    |
| ---- | --------------------------- | ------------------- | ---------------------------------------------- |
| 8.1  | Implement audit logs        | `utils/logger.py`   | Store “who did what” per table.                |
| 8.2  | Add branch support          | Extend schemas      | Add `branch_id` field to major models.         |
| 8.3  | Cloud backup & versioning   | Background cron job | Nightly Supabase export.                       |
| 8.4  | Export/import endpoints     | `reports.py`        | Export CSV/PDF/JSON.                           |
| 8.5  | Integration-ready REST APIs | All routers         | Consistent response schemas for React/Flutter. |
| 8.6  | Offline-first hybrid sync   | Local cache service | Optional — Sync on reconnection.               |

---

## 🧪 PHASE 8 — TESTING & DEPLOYMENT

### 🧰 TASK GROUP 9: Testing

| Step | Task                     | File(s)                      | Description                                 |
| ---- | ------------------------ | ---------------------------- | ------------------------------------------- |
| 9.1  | Setup pytest config      | `tests/conftest.py`          | Fixtures for Supabase client & mock tokens. |
| 9.2  | Write integration tests  | `tests/test_billing.py` etc. | CRUD tests for billing, inventory.          |
| 9.3  | Add CI/CD GitHub Actions | `.github/workflows/test.yml` | Run tests on push.                          |

---

### 🚀 TASK GROUP 10: Deployment

| Step | Task                 | Description                                          |
| ---- | -------------------- | ---------------------------------------------------- |
| 10.1 | Install dependencies | `pip install -r requirements.txt`                    |
| 10.2 | Run dev server       | `uvicorn app.main:app --reload`                      |
| 10.3 | Deploy to production | Vercel, Render, or Supabase Edge Functions for APIs. |

---

## ✅ PHASE ORDER SUMMARY

| Phase | Module                 | Description                          |
| ----- | ---------------------- | ------------------------------------ |
| 1     | Core Setup             | Config, Supabase, JWT, CORS          |
| 2     | Auth & Role Middleware | Role-based access control            |
| 3     | Billing                | Quotation → Sales → Invoice flow     |
| 4     | Inventory              | Stock, product, warehouse tracking   |
| 5     | Procurement            | Purchase orders and vendor analytics |
| 6     | Reports                | Analytics and performance dashboards |
| 7     | User & Role Admin      | User CRUD, permission management     |
| 8     | System Enhancements    | Audit, export, hybrid sync           |
| 9     | Testing                | pytest + CI/CD setup                 |
| 10    | Deployment             | Run and deploy backend               |

---
```




