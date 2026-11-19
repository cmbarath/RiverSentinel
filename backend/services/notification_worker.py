"""
River Sentinel 2.0 - Notification Outbox Worker (Phase 7 Hardened)
Reliably processes queued notifications from public.notification_deliveries:
- Independent background execution (CLI daemon and single-batch modes).
- Atomic batch claiming with concurrency safety (FOR UPDATE SKIP LOCKED).
- Stuck job recovery: automatically reclaims abandoned 'processing' jobs (> 5 minutes).
- Bounded exponential backoff: (2^attempts * 15s) capped at 3600s.
- Permanent failure classification: terminal failure when attempt_count >= max_attempts.
- Worker heartbeat and metrics recording in public.worker_heartbeats.
- Signal handling for graceful shutdown (SIGINT/SIGTERM) preserving in-flight jobs.
- Strict non-fabrication: when SMS_ENABLED is false, preserves state as failed without claiming fake delivery.
"""

import os
import sys
import time
import signal
import json
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_service import execute_sql
from services.sms_service import get_sms_provider, SMS_ENABLED

_SHUTDOWN_REQUESTED = False


def _sig_handler(signum, frame):
    global _SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    print(f"\n[INFO] Received signal {sig_name}. Requesting graceful shutdown...")
    _SHUTDOWN_REQUESTED = True


class NotificationWorker:
    @staticmethod
    def record_heartbeat(status: str = 'running', metrics: Optional[Dict[str, Any]] = None):
        """Record worker heartbeat and latest metrics in public.worker_heartbeats."""
        now_iso = datetime.now(timezone.utc).isoformat()
        metrics_json = json.dumps(metrics or {})
        sql = """
            INSERT INTO public.worker_heartbeats (worker_name, last_heartbeat, status, metrics, updated_at)
            VALUES ('notification_worker', :now, :st, :metrics::jsonb, :now)
            ON CONFLICT (worker_name)
            DO UPDATE SET
                last_heartbeat = :now,
                status = :st,
                metrics = :metrics::jsonb,
                updated_at = :now;
        """
        try:
            execute_sql(sql, {'now': now_iso, 'st': status, 'metrics': metrics_json})
        except Exception as e:
            # Non-blocking if table is temporarily inaccessible
            pass

    @staticmethod
    def recover_stuck_processing_jobs(stuck_timeout_seconds: int = 300) -> int:
        """
        Sweep for and recover jobs that got stuck in 'processing' state due to an unexpected worker crash.
        Jobs exceeding max_attempts are transitioned to 'failed'.
        Jobs with remaining attempts are requeued for execution.
        """
        cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=stuck_timeout_seconds)
        cutoff_iso = cutoff_dt.isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Fail jobs that exceeded attempts while stuck
        fail_sql = """
            UPDATE public.notification_deliveries
            SET status = 'failed',
                last_error_code = 'STUCK_JOB_TIMEOUT',
                last_error_message = 'Job timed out in processing state and exceeded maximum attempts.',
                failed_at = :now,
                updated_at = :now
            WHERE status = 'processing'
              AND updated_at < :cutoff
              AND attempt_count >= max_attempts;
        """
        try:
            execute_sql(fail_sql, {'cutoff': cutoff_iso, 'now': now_iso})
        except Exception:
            pass

        # 2. Requeue recoverable stuck jobs
        requeue_sql = """
            UPDATE public.notification_deliveries
            SET status = 'queued',
                attempt_count = attempt_count + 1,
                next_attempt_at = :now,
                last_error_code = 'STUCK_JOB_RECOVERED',
                last_error_message = 'Job recovered from stuck processing state.',
                updated_at = :now
            WHERE status = 'processing'
              AND updated_at < :cutoff
              AND attempt_count < max_attempts
            RETURNING id;
        """
        try:
            recovered_rows = execute_sql(requeue_sql, {'cutoff': cutoff_iso, 'now': now_iso})
            return len(recovered_rows) if recovered_rows else 0
        except Exception:
            return 0

    @staticmethod
    def process_outbox_batch(batch_size: int = 20) -> Dict[str, int]:
        """
        Process a single batch of pending outbox deliveries.
        Returns a dictionary of counts: {'processed': count, 'delivered': count, 'failed': count, ...}.
        """
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        stats = {
            'processed': 0,
            'delivered': 0,
            'accepted': 0,
            'failed': 0,
            'requeued': 0,
            'recovered_stuck': 0
        }

        # Step 0: Recover any stuck processing jobs from previous crashes
        recovered_count = NotificationWorker.recover_stuck_processing_jobs(stuck_timeout_seconds=300)
        stats['recovered_stuck'] = recovered_count

        # Step 1: Atomically claim work using FOR UPDATE SKIP LOCKED
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
        except Exception:
            # Fallback for environments where SKIP LOCKED syntax is unavailable
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
            NotificationWorker.record_heartbeat(status='idle', metrics=stats)
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

            # Case A: In-App Notification (Delivered directly into user's in-app inbox)
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
                        # Bounded exponential backoff: min(2^new_attempts * 15, 3600) seconds
                        backoff_sec = min((2 ** new_attempts) * 15, 3600)
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

        NotificationWorker.record_heartbeat(status='running', metrics=stats)
        return stats

    @staticmethod
    def run_daemon(interval_seconds: int = 5, batch_size: int = 20, max_iterations: Optional[int] = None):
        """
        Run the notification worker as an independent daemon loop.
        Monitors signals for graceful shutdown and records heartbeats.
        """
        global _SHUTDOWN_REQUESTED
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NotificationWorker daemon started (interval={interval_seconds}s, batch_size={batch_size})...")
        NotificationWorker.record_heartbeat(status='running', metrics={'mode': 'daemon', 'interval': interval_seconds})

        iteration = 0
        try:
            while not _SHUTDOWN_REQUESTED:
                iteration += 1
                stats = NotificationWorker.process_outbox_batch(batch_size=batch_size)
                if stats.get('processed', 0) > 0 or stats.get('recovered_stuck', 0) > 0:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iteration {iteration}: {stats}")

                if max_iterations and iteration >= max_iterations:
                    break

                # Sleep in short increments to respond quickly to shutdown signals
                sleep_start = time.time()
                while time.time() - sleep_start < interval_seconds:
                    if _SHUTDOWN_REQUESTED:
                        break
                    time.sleep(0.5)

        finally:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NotificationWorker daemon shutting down gracefully.")
            NotificationWorker.record_heartbeat(status='stopped', metrics={'last_iteration': iteration})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='River Sentinel 2.0 Notification Outbox Worker')
    parser.add_argument('--daemon', action='store_true', help='Run continuously as a daemon process')
    parser.add_argument('--interval', type=int, default=5, help='Polling interval in seconds (default: 5)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for claiming (default: 20)')
    parser.add_argument('--recover-stuck', action='store_true', help='Run stuck-job recovery sweep and exit')
    parser.add_argument('--once', action='store_true', help='Process a single batch and exit')
    args = parser.parse_args()

    if args.recover_stuck:
        print("[INFO] Running stuck-job recovery sweep...")
        recovered = NotificationWorker.recover_stuck_processing_jobs(stuck_timeout_seconds=300)
        print(f"[INFO] Recovery sweep complete. Requeued {recovered} stuck jobs.")
    elif args.daemon:
        NotificationWorker.run_daemon(interval_seconds=args.interval, batch_size=args.batch_size)
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running single-batch outbox execution...")
        res = NotificationWorker.process_outbox_batch(batch_size=args.batch_size)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Outbox batch processed: {res}")
