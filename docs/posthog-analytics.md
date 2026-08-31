# 🦔 PostHog Product Analytics Documentation

This document describes the PostHog Product Analytics integration for the **Clay Data Downloader** platform.

---

## 1. PostHog Configuration

### Required Environment Variables

PostHog configuration is loaded dynamically from system environment variables or Streamlit secrets (`st.secrets`):

```env
# PostHog API Credentials
POSTHOG_API_KEY=phc_your_actual_posthog_project_api_key_here
POSTHOG_HOST=https://us.i.posthog.com

# Application Environment Identifier (development / staging / production)
APP_ENV=production
```

> **Note**: Do NOT commit actual PostHog API keys to source control. Use `.env` or Streamlit Cloud Secrets.

### Initialization & Reusable Analytics Module

PostHog is initialized once safely via the reusable analytics helper [`analytics.py`](../analytics.py). 

* **Module**: `analytics.py`
* **Entry Point**: `init_posthog()`
* **Resiliency**: If `POSTHOG_API_KEY` is missing or invalid, analytics calls degrade gracefully without throwing runtime errors or blocking application execution.

---

## 2. User Identification & Session Management

Authenticated team members are identified using their stable user ID:

* **Identification Function**: `identify_user(user_id, properties)`
* **Tracked Non-Sensitive User Properties**:
  * `user_id`: Stable team login identifier (e.g. `team`)
  * `account_type`: `"team_member"`
  * `auth_method`: `"single_team_login"`
  * `app_environment`: `"production"` / `"development"`
* **Logout / Session Reset**: Calls `reset_user()`, which invokes `posthog.reset()` to isolate user sessions on logout.

---

## 3. Event Taxonomy Table

The table below documents every product event implemented in the Clay Data Downloader:

| Event Name | Trigger Condition | Properties Captured |
| :--- | :--- | :--- |
| `app_opened` | User opens the Streamlit application | `page_path`, `framework` |
| `page_viewed` | User switches tabs or navigates views | `page_name` |
| `user_login` | Team member logs in successfully | `user_id`, `platform` |
| `user_logout` | User clicks Logout in navigation bar | None |
| `filter_applied` | User selects an industry preset (Tech, Non-Tech, All 458) or selects target country | `filter_type`, `preset_name`, `filter_count` |
| `filter_removed` | User clicks "Clear Selection" | `filter_type`, `action` |
| `search_started` | Step 1 Count process begins | `country`, `filter_count` |
| `search_completed` | Step 1 Count process succeeds | `country`, `filter_count`, `result_count`, `duration_ms` |
| `search_failed` | Step 1 Count process encounters error | `country`, `filter_count`, `duration_ms`, `error_type` |
| `data_processing_started` | Step 2 Partition Planning begins | `country`, `industries_count`, `scope` |
| `data_processing_completed` | Step 2 Partition Planning finishes | `country`, `industries_count`, `duration_ms`, `overall_coverage_pct` |
| `data_processing_failed` | Step 2 Partition Planning encounters error | `country`, `duration_ms`, `error_type` |
| `download_started` | Step 3 Data Extraction & Download starts | `country`, `industries_count`, `file_format` (`"csv"`) |
| `download_completed` | Step 3 Data Extraction & Merge succeeds | `country`, `industries_count`, `row_count`, `unique_companies_count`, `duration_ms`, `file_format` |
| `download_failed` | Step 3 Data Extraction encounters error | `country`, `industries_count`, `duration_ms`, `error_type` |
| `export_completed` | Dataset file export or single-industry download completes | `country`, `industry`, `row_count`, `file_format` |
| `geo_config_updated` | New country geographic division setting is saved | `country`, `num_cities` |

---

## 4. Privacy & Data Protection Guarantee (CRITICAL)

Because this platform extracts company and contact records from Clay, strict data sanitization rules are enforced:

### ❌ NEVER Sent to PostHog:
* Person names, first/last names
* Email addresses
* Phone numbers
* LinkedIn URLs
* Company contact information
* Raw dataset rows or CSV contents
* Clay API keys, cookies, or session tokens
* User passwords

### ✅ ONLY Sent to PostHog:
* Quantitative counts (`row_count`, `result_count`, `unique_companies_count`, `filter_count`)
* Execution duration in milliseconds (`duration_ms`)
* File format (`"csv"`)
* High-level metadata (target country, category presets, process success/failure status)

---

## 5. Verification & Testing

To test and verify PostHog telemetry:

1. Configure environment variables in `.env` or Streamlit Cloud Secrets:
   ```env
   POSTHOG_API_KEY=phc_C9kRXc4cEpL5SrF8yb6kpBdJazYy85WmjNTm4Gh2oi5a
   POSTHOG_HOST=https://us.i.posthog.com
   ```
2. Launch the app locally:
   ```bash
   streamlit run app.py
   ```
3. Open PostHog Dashboard ➔ **Data Management ➔ Events**.
4. Log in as a user, run Step 1 Count, Step 2 Plan, and Step 3 Download.
5. Confirm that events (`user_login`, `search_completed`, `download_completed`) arrive in real time with correct `duration_ms` and `row_count` metadata without any raw data.
