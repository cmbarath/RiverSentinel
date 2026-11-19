"""
River Sentinel 2.0 - Notification Outbox Worker (Phase 5)
Reliably processes queued notifications from public.notification_deliveries:
- Atomic batch claiming with concurrency safety.
- Instant in_app notification delivery.
- Provider-independent SMS delivery with exponential backoff and rate limits.
- Strict non-fabrication: when SMS_ENABLED is false, preserves state as failed/unconfigured without claiming fake delivery.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_service import execute_sql
from services.sms_service import get_sms_provider, SMS_ENABLED


class NotificationWorker:
    @staticmethod
    def process_outbox_batch(batch_size: int = 20) -> Dict[str, int]:
        """
        Process a single batch of pending outbox deliveries.
        Returns a dictionary of counts: {'processed': count, 'delivered': count, 'failed': count}.
        """
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        stats = {'processed': 0, 'delivered': 0, 'accepted': 0, 'failed': 0, 'requeued': 0}

        # 1. Atomically claim work to prevent concurrent worker collisions
        claim_sql = """
            UPDATE public.notification_deliveries
            SET status = 'processing',
                updated_at = :now
            WHERE id IN (
                SELECT id FROM public.notification_deliveries
                WHERE status IN ('queued', 'failed')
                  AND attempt_count < max_attempts
                  AND next_attempt_at <= :now
                ORDER BY created_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, alert_id, recipient_user_id, recipient_phone, channel, provider, attempt_count, max_attempts, message_payload;
        """

        try:
            claimed_rows = execute_sql(claim_sql, {'now': now_iso, 'limit': batch_size})
        except Exception as e:
            # Fallback for environments where SKIP LOCKED syntax varies
            fallback_sql = """
                SELECT id, alert_id, recipient_user_id, recipient_phone, channel, provider, attempt_count, max_attempts, message_payload
                FROM public.notification_deliveries
                WHERE status IN ('queued', 'failed')
                  AND attempt_count < max_attempts
                  AND next_attempt_at <= :now
                ORDER BY created_at ASC
                LIMIT :limit;
            """
            claimed_rows = execute_sql(fallback_sql, {'now': now_iso, 'limit': batch_size})
            if claimed_rows:
                ids = [r[0] for r in claimed_rows]
                execute_sql("""
                    UPDATE public.notification_deliveries
                    SET status = 'processing', updated_at = :now
                    WHERE id = ANY(:ids::uuid[]);
                """, {'ids': ids, 'now': now_iso})

        if not claimed_rows:
            return stats

        sms_provider = get_sms_provider()

        for row in claimed_rows:
            delivery_id = str(row[0])
            alert_id = str(row[1])
            uid = str(row[2]) if row[2] else None
            phone = row[3]
            channel = row[4]
            provider = row[5]
            attempts = row[6]
            max_att = row[7]
            payload = row[8] or {}

            stats['processed'] += 1

            # Case A: In-App Notification (Always delivered immediately into user's inbox)
            if channel == 'in_app':
                execute_sql("""
                    UPDATE public.notification_deliveries
                    SET status = 'delivered',
                        delivered_at = :now,
                        attempt_count = attempt_count + 1,
                        updated_at = :now
                    WHERE id = :id::uuid;
                """, {'id': delivery_id, 'now': now_iso})
                stats['delivered'] += 1
                continue

            # Case B: SMS Channel
            if channel == 'sms':
                if not SMS_ENABLED and provider != 'mock':
                    # SMS Gateway is disabled in environment - do NOT fabricate delivery!
                    execute_sql("""
                        UPDATE public.notification_deliveries
                        SET status = 'failed',
                            last_error_code = 'GATEWAY_UNCONFIGURED',
                            last_error_message = 'Cellular SMS Gateway is not enabled in environment configuration.',
                            failed_at = :now,
                            attempt_count = attempt_count + 1,
                            updated_at = :now
                        WHERE id = :id::uuid;
                    """, {'id': delivery_id, 'now': now_iso})
                    stats['failed'] += 1
                    continue

                if not phone:
                    execute_sql("""
                        UPDATE public.notification_deliveries
                        SET status = 'failed',
                            last_error_code = 'NO_PHONE_NUMBER',
                            last_error_message = 'Recipient has no verified phone number on profile.',
                            failed_at = :now,
                            attempt_count = attempt_count + 1,
                            updated_at = :now
                        WHERE id = :id::uuid;
                    """, {'id': delivery_id, 'now': now_iso})
                    stats['failed'] += 1
                    continue

                # Dispatch via SMS provider
                msg_text = payload.get('text', '[River Sentinel Alert]')
                res = sms_provider.send_message(recipient_phone=phone, message=msg_text)

                if res.get('success'):
                    execute_sql("""
                        UPDATE public.notification_deliveries
                        SET status = 'accepted',
                            provider_message_id = :pmid,
                            accepted_at = :now,
                            attempt_count = attempt_count + 1,
                            updated_at = :now
                        WHERE id = :id::uuid;
                    """, {'id': delivery_id, 'pmid': res.get('provider_message_id'), 'now': now_iso})
                    stats['accepted'] += 1
                else:
                    new_attempts = attempts + 1
                    is_permanent = new_attempts >= max_att or res.get('error_code') in ('INVALID_PHONE', 'UNREGISTERED_RECIPIENT')

                    if is_permanent:
                        execute_sql("""
                            UPDATE public.notification_deliveries
                            SET status = 'failed',
                                last_error_code = :err_code,
                                last_error_message = :err_msg,
                                failed_at = :now,
                                attempt_count = :att,
                                updated_at = :now
                            WHERE id = :id::uuid;
                        """, {
                            'id': delivery_id,
                            'err_code': res.get('error_code', 'PROVIDER_ERROR'),
                            'err_msg': res.get('error_message', 'SMS dispatch rejected by provider.'),
                            'now': now_iso,
                            'att': new_attempts
                        })
                        stats['failed'] += 1
                    else:
                        # Exponential backoff retry: 2^attempts * 15 seconds
                        backoff_sec = (2 ** new_attempts) * 15
                        next_time = (now_dt + timedelta(seconds=backoff_sec)).isoformat()
                        execute_sql("""
                            UPDATE public.notification_deliveries
                            SET status = 'queued',
                                next_attempt_at = :next_t,
                                last_error_code = :err_code,
                                last_error_message = :err_msg,
                                attempt_count = :att,
                                updated_at = :now
                            WHERE id = :id::uuid;
                        """, {
                            'id': delivery_id,
                            'next_t': next_time,
                            'err_code': res.get('error_code', 'TRANSIENT_ERROR'),
                            'err_msg': res.get('error_message', 'Provider retry scheduled.'),
                            'att': new_attempts,
                            'now': now_iso
                        })
                        stats['requeued'] += 1

        return stats


if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NotificationWorker started.")
    res = NotificationWorker.process_outbox_batch()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Outbox batch processed: {res}")
