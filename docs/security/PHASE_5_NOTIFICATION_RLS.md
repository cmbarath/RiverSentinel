# River Sentinel 2.0 — Row-Level Security (RLS) & Access Control for Alerts & Notifications

## 1. Security Architecture & Threat Model

The alert and notification subsystem handles sensitive operational telemetry, environmental compliance data, and personal telephone contacts. Strict Row-Level Security (RLS) policies and Role-Based Access Control (RBAC) are enforced across Supabase PostgreSQL and Flask route decorators.

### Key Threats Mitigated:
1. **Public Panic / False Evacuation Hoaxes**: Unverified citizens or attackers cannot trigger network-wide emergency warnings.
2. **Citizen Telephone Leakage**: Personal phone numbers and delivery logs in `notification_deliveries` and `notification_preferences` are shielded from anonymous queries.
3. **Internal Node Outage Exposure**: IoT edge node hardware offline alerts (`DEVICE_HEALTH`) are strictly restricted to verified UPPCB and CWC personnel.
4. **Credential Abuse**: Backend service-role access is strictly reserved for server-side engines and worker processes.

---

## 2. PostgreSQL Row-Level Security Policies

All five alert tables have RLS explicitly enabled:

```sql
ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_deliveries ENABLE ROW LEVEL SECURITY;
```

### 2.1 `public.system_alerts` RLS Policies
- **Public & Citizen Access**:
  ```sql
  CREATE POLICY p5_alerts_public_select ON public.system_alerts
  FOR SELECT USING (
      category IN ('FLOOD', 'WATER_QUALITY') AND status != 'resolved'
  );
  ```
  Citizens can view only active environmental alerts affecting their public safety. Internal device health and administrative triage records are invisible.
- **Authority Access**:
  ```sql
  CREATE POLICY p5_alerts_authority_all ON public.system_alerts
  FOR ALL TO authenticated USING (
      EXISTS (
          SELECT 1 FROM public.profiles p
          WHERE p.id = auth.uid() AND p.role IN ('authority_admin', 'field_officer')
      )
  );
  ```

### 2.2 `public.notification_deliveries` RLS Policies
- **Recipient User Access**:
  ```sql
  CREATE POLICY p5_deliv_recipient_select ON public.notification_deliveries
  FOR SELECT TO authenticated USING (
      recipient_user_id = auth.uid()
  );
  ```
  Users can inspect only their own delivery records.
- **Recipient Mark-Read Update**:
  ```sql
  CREATE POLICY p5_deliv_recipient_update ON public.notification_deliveries
  FOR UPDATE TO authenticated USING (
      recipient_user_id = auth.uid()
  ) WITH CHECK (
      recipient_user_id = auth.uid()
  );
  ```

### 2.3 `public.notification_preferences` RLS Policies
- **Owner Access**:
  ```sql
  CREATE POLICY p5_prefs_owner_all ON public.notification_preferences
  FOR ALL TO authenticated USING (
      user_id = auth.uid()
  ) WITH CHECK (
      user_id = auth.uid()
  );
  ```

---

## 3. Backend Route-Level Access Control

Endpoints enforce role verification via decorators (`@require_auth`, `@require_role`):

| Endpoint | HTTP Method | Minimum Required Role | Purpose |
| :--- | :--- | :--- | :--- |
| `/api/v1/alerts` | `GET` | `None` (Public) / Filtered | List active public environmental alerts. Authority callers view all statuses. |
| `/api/v1/alerts/<id>` | `GET` | `None` (Public) / Full | Inspect alert metadata and event audit trail. |
| `/api/v1/alerts/<id>/acknowledge` | `POST` | `field_officer`, `authority_admin` | Acknowledge active alert with operational notes. |
| `/api/v1/alerts/<id>/resolve` | `POST` | `field_officer`, `authority_admin` | Resolve alert with mandatory resolution reason. |
| `/api/v1/alerts/rules` | `GET` | `field_officer`, `authority_admin` | List configured statutory threshold rules. |
| `/api/v1/alerts/rules` | `POST` | `authority_admin` | Create or update statutory threshold rules. |
| `/api/v1/notifications` | `GET` | Authenticated User | Retrieve user's in-app notification inbox. |
| `/api/v1/notifications/unread-count` | `GET` | Authenticated User | Retrieve unread badge count. |
| `/api/v1/notifications/<id>/read` | `POST` | Authenticated User | Mark specific in-app delivery as read. |
| `/api/v1/notifications/mark-all-read`| `POST` | Authenticated User | Mark all in-app deliveries as read. |
| `/api/v1/notifications/preferences` | `GET`, `POST` | Authenticated User | Manage user dispatch preferences and consent. |
| `/api/v1/notifications/process-outbox`| `POST` | `authority_admin` | Trigger transactional outbox dispatch batch. |
