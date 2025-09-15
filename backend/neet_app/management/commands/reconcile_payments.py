from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from neet_app.models import RazorpayOrder
from neet_app.services.razorpay_service import get_client
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile local RazorpayOrder records with Razorpay API to sync payment status"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--status',
            type=str,
            nargs='+',
            default=['initiated', 'remote_failed', 'created'],
            help='Order statuses to reconcile (default: initiated, remote_failed, created)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of orders to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        statuses = options['status']
        limit = options['limit']
        
        self.stdout.write(
            f"Starting reconciliation for orders with status: {', '.join(statuses)}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        client = get_client()
        
        # Find orders that need reconciliation
        orders_qs = RazorpayOrder.objects.filter(
            status__in=statuses
        ).exclude(
            razorpay_order_id__isnull=True
        ).exclude(
            razorpay_order_id__exact=''
        ).order_by('created_at')[:limit]
        
        orders = list(orders_qs)
        total_orders = len(orders)
        
        if total_orders == 0:
            self.stdout.write(self.style.SUCCESS("No orders found for reconciliation"))
            return
            
        self.stdout.write(f"Found {total_orders} orders to reconcile")
        
        updated_count = 0
        failed_count = 0
        
        for order in orders:
            try:
                self.stdout.write(f"Processing order {order.id} (Razorpay: {order.razorpay_order_id})")
                
                # Fetch order details from Razorpay
                try:
                    remote_order = client.order.fetch(order.razorpay_order_id)
                    remote_status = remote_order.get('status')
                    
                    self.stdout.write(f"  Remote order status: {remote_status}")
                    
                    # Fetch payments for this order
                    payments_response = client.order.payments(order.razorpay_order_id)
                    payments = payments_response.get('items', [])
                    
                    if payments:
                        # Take the most recent successful payment
                        successful_payment = None
                        for payment in payments:
                            if payment.get('status') == 'captured':
                                successful_payment = payment
                                break
                        
                        if successful_payment:
                            payment_id = successful_payment.get('id')
                            amount = successful_payment.get('amount')
                            
                            self.stdout.write(f"  Found captured payment: {payment_id}, amount: {amount}")
                            
                            if not dry_run:
                                with transaction.atomic():
                                    # Update order as paid
                                    order.razorpay_payment_id = payment_id
                                    order.status = 'paid'
                                    order.save(update_fields=['razorpay_payment_id', 'status', 'updated_at'])
                                    
                                    # Update student subscription if not already updated
                                    student = order.student
                                    if student.subscription_plan != order.plan:
                                        now = timezone.now()
                                        expires_at = now + timezone.timedelta(days=30)
                                        student.subscription_plan = order.plan
                                        student.subscription_expires_at = expires_at
                                        student.save(update_fields=['subscription_plan', 'subscription_expires_at'])
                                        
                                        self.stdout.write(f"  Updated subscription for student {student.student_id}")
                            
                            updated_count += 1
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Order {order.id} reconciled as paid"))
                            
                        else:
                            self.stdout.write(f"  No captured payments found")
                            
                    elif remote_status == 'paid':
                        # Order is marked as paid but no payment details available
                        self.stdout.write(f"  Order marked as paid remotely but no payment details")
                        if not dry_run:
                            order.status = 'paid'
                            order.save(update_fields=['status', 'updated_at'])
                        updated_count += 1
                        
                    else:
                        self.stdout.write(f"  Order not paid remotely (status: {remote_status})")
                        
                except Exception as api_exc:
                    self.stdout.write(
                        self.style.ERROR(f"  Failed to fetch from Razorpay API: {str(api_exc)}")
                    )
                    failed_count += 1
                    continue
                    
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  Error processing order {order.id}: {str(exc)}")
                )
                failed_count += 1
                logger.exception(f"Error reconciling order {order.id}")
                
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Reconciliation complete:")
        self.stdout.write(f"  Total processed: {total_orders}")
        self.stdout.write(f"  Successfully updated: {updated_count}")
        self.stdout.write(f"  Failed: {failed_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No actual changes were made"))
        elif updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully reconciled {updated_count} orders"))