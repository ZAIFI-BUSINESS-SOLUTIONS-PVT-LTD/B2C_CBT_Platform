import json
import logging
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from ..services.razorpay_service import get_client
from ..models import RazorpayOrder
from ..models import StudentProfile
from django.db import IntegrityError

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """
    Handle Razorpay webhook events for payment reconciliation
    
    POST /api/payments/webhook/razorpay/
    Headers: X-Razorpay-Signature
    Body: JSON payload from Razorpay
    """
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    body = request.body
    
    # Check if webhook signature and secret are configured
    if not signature:
        logger.warning("Razorpay webhook received without signature")
        return HttpResponseForbidden("Missing signature")
    
    if not hasattr(settings, 'RAZORPAY_WEBHOOK_SECRET') or not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("Razorpay webhook secret not configured (RAZORPAY_WEBHOOK_SECRET)")
        return HttpResponseForbidden("Webhook not configured")
    
    logger.debug(f"Webhook signature verification - body length: {len(body)}, signature present: {bool(signature)}")
    logger.debug(f"Webhook secret configured: {bool(settings.RAZORPAY_WEBHOOK_SECRET)}")

    # Verify webhook signature
    client = get_client()
    try:
        # Ensure body is a string for Razorpay verification
        if isinstance(body, bytes):
            body_str = body.decode('utf-8')
        else:
            body_str = body
        
        client.utility.verify_webhook_signature(
            body_str, signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
        logger.debug("Razorpay webhook signature verification successful")
    except Exception as exc:
        logger.warning(f"Razorpay webhook signature verification failed: {str(exc)}")
        return HttpResponseForbidden("Invalid signature")

    # Parse webhook payload
    try:
        # Use the string version of body for JSON parsing
        if isinstance(body, bytes):
            payload = json.loads(body.decode('utf-8'))
        else:
            payload = json.loads(body)
            
        event = payload.get('event')
        data = payload.get('payload', {})
        
        logger.info(f"Received Razorpay webhook event: {event}")
        
        # Handle different webhook events
        if event == 'payment.captured':
            _handle_payment_captured(data)
        elif event == 'payment.failed':
            _handle_payment_failed(data)
        elif event == 'order.paid':
            _handle_order_paid(data)
        elif event.startswith('refund.'):
            _handle_refund_event(event, data)
        else:
            logger.info(f"Unhandled webhook event: {event}")
        
        return JsonResponse({"status": "ok"})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as exc:
        logger.exception(f"Error processing Razorpay webhook: {str(exc)}")
        return HttpResponse("Webhook processing failed", status=500)


def _handle_payment_captured(data):
    """Handle payment.captured webhook event"""
    try:
        payment_entity = data.get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        amount = payment_entity.get('amount')  # in paise
        
        if not order_id or not payment_id:
            logger.warning("payment.captured webhook missing order_id or payment_id")
            return
        
        with transaction.atomic():
            try:
                rp_order = RazorpayOrder.objects.select_for_update().get(
                    razorpay_order_id=order_id
                )
                
                if rp_order.status != 'paid':
                    # Update order status
                    rp_order.razorpay_payment_id = payment_id
                    rp_order.status = 'paid'
                    rp_order.save(update_fields=['razorpay_payment_id', 'status', 'updated_at'])
                    
                    # Update student subscription if not already updated
                    student = rp_order.student
                    if student.subscription_plan != rp_order.plan:
                        now = timezone.now()
                        expires_at = now + timedelta(days=30)
                        student.subscription_plan = rp_order.plan
                        student.subscription_expires_at = expires_at
                        student.save(update_fields=['subscription_plan', 'subscription_expires_at'])
                    
                    logger.info(f"Webhook: Updated order {rp_order.id} to paid via payment.captured")
                else:
                    logger.info(f"Webhook: Order {rp_order.id} already marked as paid")
                    
            except RazorpayOrder.DoesNotExist:
                logger.warning(f"Webhook payment.captured for unknown order {order_id}")
                
    except Exception as exc:
        logger.exception(f"Error handling payment.captured webhook: {str(exc)}")


def _handle_payment_failed(data):
    """Handle payment.failed webhook event"""
    try:
        payment_entity = data.get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        
        if not order_id:
            logger.warning("payment.failed webhook missing order_id")
            return
            
        try:
            rp_order = RazorpayOrder.objects.get(razorpay_order_id=order_id)
            if rp_order.status not in ['paid', 'failed']:
                rp_order.status = 'failed'
                rp_order.save(update_fields=['status', 'updated_at'])
                logger.info(f"Webhook: Updated order {rp_order.id} to failed via payment.failed")
                
        except RazorpayOrder.DoesNotExist:
            logger.warning(f"Webhook payment.failed for unknown order {order_id}")
            
    except Exception as exc:
        logger.exception(f"Error handling payment.failed webhook: {str(exc)}")


def _handle_order_paid(data):
    """Handle order.paid webhook event"""
    try:
        order_entity = data.get('order', {}).get('entity', {})
        order_id = order_entity.get('id')
        
        if not order_id:
            logger.warning("order.paid webhook missing order_id")
            return
            
        # Similar logic to payment.captured but for order-level events
        _handle_payment_captured(data)
        
    except Exception as exc:
        logger.exception(f"Error handling order.paid webhook: {str(exc)}")


def _handle_refund_event(event, data):
    """Handle refund.* webhook events"""
    try:
        refund_entity = data.get('refund', {}).get('entity', {})
        payment_id = refund_entity.get('payment_id')
        refund_amount = refund_entity.get('amount')  # in paise
        refund_status = refund_entity.get('status')
        refund_id = refund_entity.get('id')
        
        if not payment_id:
            logger.warning(f"{event} webhook missing payment_id")
            return
            
        try:
            rp_order = RazorpayOrder.objects.get(razorpay_payment_id=payment_id)

            # Create or update a lightweight refund record on the order
            # We'll store refund details in a small JSON field on the order if available,
            # otherwise log and create an admin-visible record via logger.
            try:
                # If order has a 'refunds' JSONField, append. Otherwise, log structured info.
                if hasattr(rp_order, 'refunds'):
                    refunds = rp_order.refunds or []
                    refunds.append({
                        'refund_id': refund_id,
                        'amount': refund_amount,
                        'status': refund_status,
                        'created_at': None
                    })
                    rp_order.refunds = refunds
                    rp_order.save(update_fields=['refunds', 'updated_at'])
                else:
                    # No refunds field on model; log the event and proceed
                    logger.info(f"Webhook: Refund {refund_status} (id={refund_id}) for order {rp_order.id}, amount={refund_amount}, payment={payment_id}")
            except IntegrityError:
                logger.exception("Failed to save refund details on order %s", rp_order.id)

            # If refund is processed and amount equals order amount, mark order refunded and revoke subscription
            try:
                # Compare amounts (paise)
                if refund_status in ['processed', 'success'] or refund_status == 'processed':
                    # `refund_amount` from Razorpay is in paise; `rp_order.amount` now stored in rupees
                    try:
                        order_amount_paise = int(rp_order.amount) * 100
                    except Exception:
                        order_amount_paise = None

                    if refund_amount and rp_order.amount and order_amount_paise is not None and int(refund_amount) >= int(order_amount_paise):
                        rp_order.status = 'refunded'
                        rp_order.save(update_fields=['status', 'updated_at'])

                        # Revoke student's subscription if it matches the refunded plan
                        student = rp_order.student
                        if student.subscription_plan == rp_order.plan:
                            student.subscription_plan = None
                            student.subscription_expires_at = None
                            student.save(update_fields=['subscription_plan', 'subscription_expires_at'])
                            logger.info(f"Webhook: Revoked subscription for student {student.student_id} due to full refund of order {rp_order.id}")

                        logger.info(f"Webhook: Marked order {rp_order.id} as refunded (refund_id={refund_id})")
                    else:
                        logger.info(f"Webhook: Partial refund for order {rp_order.id} (refund_id={refund_id}, amount={refund_amount})")
                else:
                    logger.info(f"Webhook: Refund event {refund_status} for order {rp_order.id} (refund_id={refund_id}, amount={refund_amount})")
            except Exception:
                logger.exception("Error processing refund status for order %s", rp_order.id)

        except RazorpayOrder.DoesNotExist:
            logger.warning(f"Webhook {event} for unknown payment {payment_id}")
            
    except Exception as exc:
        logger.exception(f"Error handling {event} webhook: {str(exc)}")