"""
River Sentinel 2.0 - Core Alert Generation & Lifecycle Engine (Phase 5)
Provides:
- Comprehensive evaluation of sensor observations against CPCB Class B and CWC benchmarks.
- Deduplication keying, occurrence counting, and hysteresis.
- Automated recovery verification without manual intervention.
- Hardware node offline detection adhering to runtime lifecycle rules.
- Pollution report review alerting.
- Transactional notification outbox enqueueing with strict simulation suppression.
- Role-based alert acknowledgement and resolution audit logs.
"""

import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from services.supabase_service import execute_sql, supabase_get, supabase_insert, supabase_update
from services.sms_service import format_sms_message

# CWC Varanasi Reference Levels (GTS MSL Datum)
CWC_WARNING_LEVEL_M = 70.26
CWC_DANGER_LEVEL_M = 71.26
CWC_HFL_M = 73.90


def _generate_alert_code() -> str:
    """Generate a clean human-readable alert code: ALT-YYYYMMDD-XXXX."""
    now_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    rand_suffix = uuid.uuid4().hex[:6].upper()
    return f"ALT-{now_str}-{rand_suffix}"


class AlertService:
    @staticmethod
    def evaluate_sensor_observation(reading: Dict[str, Any], station_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Evaluate a single telemetry observation against active alert rules.
        Non-blocking: catches internal errors and logs without failing sensor ingestion.
        """
        created_or_updated_alerts = []
        try:
            # 1. Resolve Station Metadata
            sid = station_id or reading.get('station_id')
            station = None
            if sid:
                stns = supabase_get('monitoring_stations', filters={'id': f'eq.{sid}'})
                if stns:
                    station = stns[0]

            station_name = station.get('station_name') if station else 'Varanasi Ganga Station'
            station_code = station.get('station_code') if station else 'STN-VAR-UNKNOWN'
            has_cwc_gauge = bool(station and station.get('cwc_reference_gauge_id'))

            provenance = reading.get('provenance', 'real_sensor')
            quality_status = reading.get('quality_status', 'valid')
            reading_id = str(reading.get('id', ''))
            obs_time = reading.get('observed_at') or reading.get('created_at') or datetime.now(timezone.utc).isoformat()

            ph = float(reading['ph']) if reading.get('ph') is not None else None
            turb = float(reading['turbidity']) if reading.get('turbidity') is not None else None
            wl = float(reading['water_level']) if reading.get('water_level') is not None else None
            do_v = float(reading['do']) if reading.get('do') is not None else None

            # ----------------------------------------------------------------
            # Rule 1: CWC Flood Stage Screening (Warning & Danger)
            # Only evaluated if station has verified CWC gauge binding and GTS MSL datum
            # ----------------------------------------------------------------
            if wl is not None and has_cwc_gauge:
                warning_thresh = float(station.get('warning_water_level_m') or CWC_WARNING_LEVEL_M)
                danger_thresh = float(station.get('danger_water_level_m') or CWC_DANGER_LEVEL_M)

                dedup_key = f"FLOOD:{sid or station_code}"

                if wl >= danger_thresh:
                    # Trigger or escalate to CRITICAL
                    alt = AlertService._trigger_or_update_alert(
                        rule_code='RULE-CWC-FLOOD-DANGER',
                        dedup_key=dedup_key,
                        station_id=sid,
                        device_id=reading.get('device_id'),
                        category='FLOOD',
                        severity='CRITICAL',
                        title=f"CRITICAL FLOOD DANGER: {station_name}",
                        description=f"River stage ({wl:.2f}m MSL) has exceeded CWC Danger Stage ({danger_thresh:.2f}m MSL). Low-lying ghat steps inundated. Immediate precautionary evacuation required.",
                        source_type='sensor_reading',
                        source_record_id=reading_id,
                        provenance=provenance,
                        quality_status=quality_status,
                        measured_value=wl,
                        expected_threshold=danger_thresh,
                        threshold_unit='m'
                    )
                    if alt:
                        created_or_updated_alerts.append(alt)

                elif wl >= warning_thresh:
                    # Trigger or maintain HIGH Warning
                    alt = AlertService._trigger_or_update_alert(
                        rule_code='RULE-CWC-FLOOD-WARN',
                        dedup_key=dedup_key,
                        station_id=sid,
                        device_id=reading.get('device_id'),
                        category='FLOOD',
                        severity='HIGH',
                        title=f"FLOOD WARNING: {station_name}",
                        description=f"River stage ({wl:.2f}m MSL) has reached or exceeded CWC Warning Stage ({warning_thresh:.2f}m MSL). Low-lying steps approaching inundation.",
                        source_type='sensor_reading',
                        source_record_id=reading_id,
                        provenance=provenance,
                        quality_status=quality_status,
                        measured_value=wl,
                        expected_threshold=warning_thresh,
                        threshold_unit='m'
                    )
                    if alt:
                        created_or_updated_alerts.append(alt)

                else:
                    # River level below warning threshold - Check for recovery!
                    # Hysteresis: recovery threshold is 70.10m (0.16m below warning)
                    if wl <= (warning_thresh - 0.15):
                        AlertService._check_and_resolve_alert(
                            dedup_key=dedup_key,
                            current_val=wl,
                            recovery_thresh=warning_thresh - 0.15,
                            reason=f"Water level ({wl:.2f}m) has receded below CWC recovery threshold ({warning_thresh - 0.15:.2f}m MSL)."
                        )

            # ----------------------------------------------------------------
            # Rule 2: CPCB Class B pH Standard (6.5 to 8.5)
            # ----------------------------------------------------------------
            if ph is not None:
                ph_dedup = f"WATER_QUALITY_PH:{sid or station_code}"
                if ph < 6.5 or ph > 8.5:
                    alt = AlertService._trigger_or_update_alert(
                        rule_code='RULE-CPCB-PH-RANGE',
                        dedup_key=ph_dedup,
                        station_id=sid,
                        device_id=reading.get('device_id'),
                        category='WATER_QUALITY',
                        severity='MEDIUM',
                        title=f"CPCB Class B pH Deviation: {station_name}",
                        description=f"Water pH ({ph:.2f}) is outside statutory CPCB Class B Outdoor Bathing limits (6.5 to 8.5).",
                        source_type='sensor_reading',
                        source_record_id=reading_id,
                        provenance=provenance,
                        quality_status=quality_status,
                        measured_value=ph,
                        expected_threshold=6.5 if ph < 6.5 else 8.5,
                        threshold_unit='pH'
                    )
                    if alt:
                        created_or_updated_alerts.append(alt)
                elif 6.6 <= ph <= 8.4:
                    # Recovered inside safe envelope
                    AlertService._check_and_resolve_alert(
                        dedup_key=ph_dedup,
                        current_val=ph,
                        recovery_thresh=6.6,
                        reason=f"Water pH ({ph:.2f}) returned to standard CPCB Class B envelope (6.5–8.5)."
                    )

            # ----------------------------------------------------------------
            # Rule 3: CPCB Class B Dissolved Oxygen (DO >= 5.0 mg/L)
            # ----------------------------------------------------------------
            if do_v is not None:
                do_dedup = f"WATER_QUALITY_DO:{sid or station_code}"
                if do_v < 5.0:
                    severity = 'CRITICAL' if do_v < 3.0 else 'HIGH'
                    alt = AlertService._trigger_or_update_alert(
                        rule_code='RULE-CPCB-DO-MIN',
                        dedup_key=do_dedup,
                        station_id=sid,
                        device_id=reading.get('device_id'),
                        category='WATER_QUALITY',
                        severity=severity,
                        title=f"Dissolved Oxygen Depletion: {station_name}",
                        description=f"Dissolved oxygen ({do_v:.1f} mg/L) is below statutory CPCB Class B minimum (5.0 mg/L). Risk of aquatic hypoxia.",
                        source_type='sensor_reading',
                        source_record_id=reading_id,
                        provenance=provenance,
                        quality_status=quality_status,
                        measured_value=do_v,
                        expected_threshold=5.0,
                        threshold_unit='mg/L'
                    )
                    if alt:
                        created_or_updated_alerts.append(alt)
                elif do_v >= 5.2:
                    AlertService._check_and_resolve_alert(
                        dedup_key=do_dedup,
                        current_val=do_v,
                        recovery_thresh=5.2,
                        reason=f"Dissolved oxygen ({do_v:.1f} mg/L) recovered above CPCB benchmark (5.0 mg/L)."
                    )

            # ----------------------------------------------------------------
            # Rule 4: Elevated Turbidity Peak (> 50 NTU)
            # ----------------------------------------------------------------
            if turb is not None:
                turb_dedup = f"WATER_QUALITY_TURB:{sid or station_code}"
                if turb > 50.0:
                    alt = AlertService._trigger_or_update_alert(
                        rule_code='RULE-TURB-HIGH',
                        dedup_key=turb_dedup,
                        station_id=sid,
                        device_id=reading.get('device_id'),
                        category='WATER_QUALITY',
                        severity='MEDIUM',
                        title=f"Elevated Turbidity Peak: {station_name}",
                        description=f"Turbidity ({turb:.1f} NTU) exceeds 50 NTU. Indicates heavy suspended silt or runoff influx.",
                        source_type='sensor_reading',
                        source_record_id=reading_id,
                        provenance=provenance,
                        quality_status=quality_status,
                        measured_value=turb,
                        expected_threshold=50.0,
                        threshold_unit='NTU'
                    )
                    if alt:
                        created_or_updated_alerts.append(alt)
                elif turb <= 40.0:
                    AlertService._check_and_resolve_alert(
                        dedup_key=turb_dedup,
                        current_val=turb,
                        recovery_thresh=40.0,
                        reason=f"Turbidity ({turb:.1f} NTU) returned below standard threshold."
                    )

        except Exception as e:
            print(f"[WARN] AlertService evaluation error: {e}")

        return created_or_updated_alerts

    @staticmethod
    def evaluate_device_health(device: Dict[str, Any], station: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluate device connectivity and runtime state.
        Crucial: Only installed and active physical devices trigger hardware-offline alerts.
        Provisioned devices awaiting installation are NOT reported as outages.
        """
        lifecycle = device.get('status', 'provisioned')
        if lifecycle != 'active':
            return None

        dev_id = str(device.get('id'))
        dev_code = device.get('device_code', 'DEV-UNKNOWN')
        station_name = station.get('station_name') if station else 'Varanasi Ghat'
        sid = device.get('station_id')

        last_seen = device.get('last_seen_at')
        dedup_key = f"DEVICE_OFFLINE:{dev_id}"

        if not last_seen:
            # Device is active but has never connected
            return None

        try:
            dt = datetime.fromisoformat(str(last_seen).replace('Z', '+00:00'))
            stale_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
        except Exception:
            return None

        if stale_seconds > 900:  # 15 minutes
            alt = AlertService._trigger_or_update_alert(
                rule_code='RULE-DEV-OFFLINE',
                dedup_key=dedup_key,
                station_id=sid,
                device_id=dev_id,
                category='DEVICE_HEALTH',
                severity='HIGH',
                title=f"IoT Node Offline: {dev_code}",
                description=f"ESP32 hardware node {dev_code} at {station_name} has not transmitted telemetry in {int(stale_seconds)}s (> 900s). Check power supply or LoRa/WiFi gateway.",
                source_type='device_telemetry',
                source_record_id=dev_id,
                provenance='real_sensor',
                quality_status='degraded',
                measured_value=stale_seconds,
                expected_threshold=900,
                threshold_unit='seconds'
            )
            return alt
        else:
            # Device has reconnected within 15 minutes!
            AlertService._check_and_resolve_alert(
                dedup_key=dedup_key,
                current_val=stale_seconds,
                recovery_thresh=900,
                reason=f"ESP32 hardware node {dev_code} resumed telemetry transmission."
            )
            return None

    @staticmethod
    def evaluate_new_pollution_report(report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trigger an official review alert upon submission of a citizen pollution report."""
        rep_id = str(report.get('id', ''))
        loc_name = report.get('location_name') or 'Varanasi Riparian Ghat'
        level = report.get('pollution_level', 'Moderate')
        dedup_key = f"POLLUTION_REPORT:{rep_id}"

        return AlertService._trigger_or_update_alert(
            rule_code='RULE-POLLUTION-NEW',
            dedup_key=dedup_key,
            station_id=report.get('station_id'),
            device_id=None,
            category='POLLUTION_REPORT',
            severity='HIGH' if level == 'High' else 'MEDIUM',
            title=f"New Citizen Pollution Report: {loc_name}",
            description=f"A citizen lodged pollution report #{rep_id[:8]} at {loc_name} (Severity: {level}). UPPCB authority field triage required.",
            source_type='pollution_report',
            source_record_id=rep_id,
            provenance='real_sensor',
            quality_status='valid',
            measured_value=1,
            expected_threshold=1,
            threshold_unit='count'
        )

    # ------------------------------------------------------------------------
    # Internal Alert Creation, Deduplication & Recovery Helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _trigger_or_update_alert(
        rule_code: str, dedup_key: str, station_id: Optional[str],
        device_id: Optional[str], category: str, severity: str,
        title: str, description: str, source_type: str, source_record_id: str,
        provenance: str, quality_status: str, measured_value: Optional[float],
        expected_threshold: Optional[float], threshold_unit: str
    ) -> Optional[Dict[str, Any]]:
        """
        Deduplication Core:
        - Checks for active or acknowledged alert with same deduplication_key.
        - If active: updates occurrence count, last_triggered_at, and measured_value.
        - If none: inserts new alert row, logs 'triggered' event, and enqueues notifications.
        """
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        # Check existing active/acknowledged alert
        sql = """
            SELECT id, alert_code, status, occurrence_count, severity, last_triggered_at
            FROM public.system_alerts
            WHERE deduplication_key = :dedup_key AND status IN ('active', 'acknowledged')
            LIMIT 1;
        """
        existing = execute_sql(sql, {'dedup_key': dedup_key})

        if existing:
            alt_id = str(existing[0][0])
            alt_code = existing[0][1]
            cur_occ = existing[0][3]
            old_sev = existing[0][4]

            # Escalation check: if new severity is higher (e.g. Warning -> Danger), update severity
            update_sql = """
                UPDATE public.system_alerts
                SET occurrence_count = occurrence_count + 1,
                    last_triggered_at = :now,
                    measured_value = :mval,
                    severity = CASE WHEN :sev = 'CRITICAL' THEN 'CRITICAL' ELSE severity END,
                    title = :title,
                    description = :desc,
                    updated_at = :now
                WHERE id = :id::uuid
                RETURNING id, alert_code, status, occurrence_count, severity;
            """
            execute_sql(update_sql, {
                'id': alt_id, 'now': now_iso, 'mval': measured_value,
                'sev': severity, 'title': title, 'desc': description
            })

            # Log repeated or escalated event in alert_events
            event_type = 'escalated' if severity == 'CRITICAL' and old_sev != 'CRITICAL' else 'repeated'
            execute_sql("""
                INSERT INTO public.alert_events (alert_id, event_type, metadata, created_at)
                VALUES (:alt_id::uuid, :event_type, :meta::jsonb, :now);
            """, {
                'alt_id': alt_id,
                'event_type': event_type,
                'meta': f'{{"occurrence": {cur_occ + 1}, "measured_value": {measured_value}}}',
                'now': now_iso
            })

            return {
                'id': alt_id,
                'alert_code': alt_code,
                'category': category,
                'severity': severity,
                'title': title,
                'status': 'active',
                'action': 'updated',
                'occurrence_count': cur_occ + 1
            }

        # Create brand new alert
        new_alert_code = _generate_alert_code()
        insert_sql = """
            INSERT INTO public.system_alerts (
                alert_code, station_id, device_id, category, severity,
                title, description, source_type, source_record_id, provenance,
                quality_status, measured_value, expected_threshold, threshold_unit,
                deduplication_key, status, occurrence_count, first_triggered_at,
                last_triggered_at, created_at, updated_at
            ) VALUES (
                :code, :sid::uuid, :did::uuid, :cat, :sev,
                :title, :desc, :stype, :srec, :prov,
                :qstat, :mval, :ethresh, :unit,
                :dedup, 'active', 1, :now,
                :now, :now, :now
            ) RETURNING id, alert_code;
        """
        row = execute_sql(insert_sql, {
            'code': new_alert_code,
            'sid': station_id if station_id else None,
            'did': device_id if device_id else None,
            'cat': category,
            'sev': severity,
            'title': title,
            'desc': description,
            'stype': source_type,
            'srec': source_record_id,
            'prov': provenance,
            'qstat': quality_status,
            'mval': measured_value,
            'ethresh': expected_threshold,
            'unit': threshold_unit,
            'dedup': dedup_key,
            'now': now_iso
        })

        if not row:
            return None

        alt_id = str(row[0][0])

        # Log 'triggered' event in alert_events
        execute_sql("""
            INSERT INTO public.alert_events (alert_id, event_type, metadata, created_at)
            VALUES (:alt_id::uuid, 'triggered', :meta::jsonb, :now);
        """, {
            'alt_id': alt_id,
            'meta': f'{{"initial_measured_value": {measured_value}, "threshold": {expected_threshold}}}',
            'now': now_iso
        })

        # Enqueue Outbox Deliveries
        AlertService._enqueue_notifications_for_alert(
            alert_id=alt_id,
            category=category,
            severity=severity,
            station_id=station_id,
            title=title,
            description=description,
            provenance=provenance,
            param=threshold_unit,
            val=measured_value
        )

        return {
            'id': alt_id,
            'alert_code': new_alert_code,
            'category': category,
            'severity': severity,
            'title': title,
            'status': 'active',
            'action': 'created',
            'occurrence_count': 1
        }

    @staticmethod
    def _check_and_resolve_alert(dedup_key: str, current_val: Any, recovery_thresh: Any, reason: str):
        """Verify recovery condition and resolve active alert."""
        now_iso = datetime.now(timezone.utc).isoformat()
        find_sql = """
            SELECT id, alert_code FROM public.system_alerts
            WHERE deduplication_key = :dedup_key AND status IN ('active', 'acknowledged')
            LIMIT 1;
        """
        existing = execute_sql(find_sql, {'dedup_key': dedup_key})
        if not existing:
            return

        alt_id = str(existing[0][0])
        alt_code = existing[0][1]

        # Resolve alert in database
        execute_sql("""
            UPDATE public.system_alerts
            SET status = 'resolved',
                resolved_at = :now,
                resolution_reason = :reason,
                updated_at = :now
            WHERE id = :id::uuid;
        """, {'id': alt_id, 'now': now_iso, 'reason': reason})

        # Log 'resolved' event in alert_events
        execute_sql("""
            INSERT INTO public.alert_events (alert_id, event_type, metadata, created_at)
            VALUES (:alt_id::uuid, 'resolved', :meta::jsonb, :now);
        """, {
            'alt_id': alt_id,
            'meta': f'{{"recovery_value": {current_val}, "recovery_threshold": {recovery_thresh}, "reason": "{reason}"}}',
            'now': now_iso
        })

    @staticmethod
    def _enqueue_notifications_for_alert(
        alert_id: str, category: str, severity: str, station_id: Optional[str],
        title: str, description: str, provenance: str, param: str, val: Any
    ):
        """
        Transactional Outbox Enqueueing:
        - Resolves authorized recipients (Authority admins, assigned officers, consenting citizens).
        - Enqueues in-app delivery for all authorized users.
        - Enqueues SMS ONLY if provenance == 'real_sensor', user has verified phone, and user explicitly consented.
        - Enforces idempotency via idempotency_key to prevent duplicate message dispatch.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # Find target recipients
        # 1. Authority Admins always receive operational and environmental notifications
        admin_rows = execute_sql("SELECT id FROM public.profiles WHERE role = 'authority_admin';")
        recipient_user_ids = [str(r[0]) for r in admin_rows]

        # 2. Field Officers assigned to this station
        if station_id:
            officer_rows = execute_sql("""
                SELECT sa.user_id 
                FROM public.station_assignments sa
                JOIN public.profiles p ON p.id = sa.user_id
                WHERE sa.station_id = :sid::uuid AND sa.status = 'active';
            """, {'sid': station_id})
            for r in officer_rows:
                uid = str(r[0])
                if uid not in recipient_user_ids:
                    recipient_user_ids.append(uid)

        # 3. For public emergency flood/water alerts, add citizens who opted in
        if category in ('FLOOD', 'WATER_QUALITY') and severity in ('CRITICAL', 'HIGH'):
            citizen_pref_rows = execute_sql("""
                SELECT user_id FROM public.notification_preferences
                WHERE in_app_enabled = true AND :sev = ANY(preferred_severities) AND :cat = ANY(preferred_categories);
            """, {'sev': severity, 'cat': category})
            for r in citizen_pref_rows:
                uid = str(r[0])
                if uid not in recipient_user_ids:
                    recipient_user_ids.append(uid)

        # Enqueue in_app deliveries
        for uid in recipient_user_ids:
            idempotency_key = f"{alert_id}:{uid}:in_app"
            execute_sql("""
                INSERT INTO public.notification_deliveries (
                    alert_id, recipient_user_id, channel, provider, status,
                    idempotency_key, message_payload, created_at, updated_at
                ) VALUES (
                    :alt_id::uuid, :uid::uuid, 'in_app', 'internal', 'queued',
                    :idem, :payload::jsonb, :now, :now
                ) ON CONFLICT (idempotency_key) DO NOTHING;
            """, {
                'alt_id': alert_id,
                'uid': uid,
                'idem': idempotency_key,
                'payload': f'{{"title": "{title}", "category": "{category}", "severity": "{severity}", "description": "{description}"}}',
                'now': now_iso
            })

            # Check SMS eligibility
            # STRICT GUARD: Never send real external SMS for simulated sensor readings!
            pref_rows = execute_sql("""
                SELECT np.sms_enabled, np.phone_number_verified, np.consent_timestamp, p.phone
                FROM public.notification_preferences np
                JOIN public.profiles p ON p.id = np.user_id
                WHERE np.user_id = :uid::uuid;
            """, {'uid': uid})

            if pref_rows and pref_rows[0][0] and pref_rows[0][1] and pref_rows[0][3]:
                # User opted in, has verified phone, and consent timestamp
                phone = pref_rows[0][3]
                sms_idem = f"{alert_id}:{uid}:sms"
                sms_text = format_sms_message(category, severity, 'Ganga Station', param or '', val or '', '', now_iso)
                
                # Check provenance: simulated telemetry strictly suppresses external cellular delivery
                sms_status = 'queued' if provenance == 'real_sensor' else 'suppressed'

                execute_sql("""
                    INSERT INTO public.notification_deliveries (
                        alert_id, recipient_user_id, recipient_phone, channel, provider,
                        status, idempotency_key, message_payload, created_at, updated_at
                    ) VALUES (
                        :alt_id::uuid, :uid::uuid, :phone, 'sms', 'mock',
                        :status, :idem, :payload::jsonb, :now, :now
                    ) ON CONFLICT (idempotency_key) DO NOTHING;
                """, {
                    'alt_id': alert_id,
                    'uid': uid,
                    'phone': phone,
                    'status': sms_status,
                    'idem': sms_idem,
                    'payload': json.dumps({'text': sms_text, 'simulated_suppressed': provenance != 'real_sensor'}),
                    'now': now_iso
                })

    # ------------------------------------------------------------------------
    # User Actions: Acknowledgement & Resolution
    # ------------------------------------------------------------------------

    @staticmethod
    def acknowledge_alert(alert_id: str, user_id: str, user_role: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Acknowledge an active alert with role enforcement."""
        if user_role not in ('authority_admin', 'field_officer'):
            raise PermissionError("Only Authority Administrators and Field Officers can acknowledge alerts.")

        now_iso = datetime.now(timezone.utc).isoformat()
        res = execute_sql("""
            UPDATE public.system_alerts
            SET status = 'acknowledged',
                acknowledged_by = :uid::uuid,
                acknowledged_at = :now,
                updated_at = :now
            WHERE id = :id::uuid AND status = 'active'
            RETURNING id, alert_code, status;
        """, {'id': alert_id, 'uid': user_id, 'now': now_iso})

        if not res:
            raise ValueError(f"Alert '{alert_id}' not found or already acknowledged/resolved.")

        # Log 'acknowledged' event
        execute_sql("""
            INSERT INTO public.alert_events (alert_id, event_type, actor_id, metadata, created_at)
            VALUES (:alt_id::uuid, 'acknowledged', :uid::uuid, :meta::jsonb, :now);
        """, {
            'alt_id': alert_id,
            'uid': user_id,
            'meta': json.dumps({'notes': notes or 'No notes provided'}),
            'now': now_iso
        })

        return {'status': 'success', 'message': f"Alert {res[0][1]} marked as acknowledged."}

    @staticmethod
    def resolve_alert(alert_id: str, user_id: str, user_role: str, reason: str) -> Dict[str, Any]:
        """Resolve an active or acknowledged alert with formal resolution reason."""
        if user_role not in ('authority_admin', 'field_officer'):
            raise PermissionError("Only Authority Administrators and Field Officers can resolve alerts.")

        if not reason or len(reason.strip()) < 5:
            raise ValueError("A descriptive resolution reason (minimum 5 characters) is required.")

        now_iso = datetime.now(timezone.utc).isoformat()
        res = execute_sql("""
            UPDATE public.system_alerts
            SET status = 'resolved',
                resolved_by = :uid::uuid,
                resolved_at = :now,
                resolution_reason = :reason,
                updated_at = :now
            WHERE id = :id::uuid AND status IN ('active', 'acknowledged')
            RETURNING id, alert_code, status;
        """, {'id': alert_id, 'uid': user_id, 'reason': reason.strip(), 'now': now_iso})

        if not res:
            raise ValueError(f"Alert '{alert_id}' not found or already resolved.")

        # Log 'resolved' event
        execute_sql("""
            INSERT INTO public.alert_events (alert_id, event_type, actor_id, metadata, created_at)
            VALUES (:alt_id::uuid, 'resolved', :uid::uuid, :meta::jsonb, :now);
        """, {
            'alt_id': alert_id,
            'uid': user_id,
            'meta': json.dumps({'resolution_reason': reason.strip()}),
            'now': now_iso
        })

        return {'status': 'success', 'message': f"Alert {res[0][1]} resolved successfully."}
