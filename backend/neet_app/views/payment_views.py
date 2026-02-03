from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import logging

from ..models import RazorpayOrder, StudentProfile
from ..serializers import CreateOrderSerializer, VerifyPaymentSerializer
from ..services.razorpay_service import create_order, verify_payment_signature
from ..services.razorpay_service import get_client
from django.conf import settings
import razorpay
import json

logger = logging.getLogger(__name__)

# Define server-side plan pricing (INR)
PLANS = {
    "basic": 720,  # rupees
    "pro": 7200,
}

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order_view(request):
    """
    Create a Razorpay order for the specified plan
    
    POST /api/payments/create-order/
    Body: {"plan": "basic" | "pro"}
    """
    logger.debug(f"create_order_view called by user={getattr(request.user, 'student_id', request.user)} headers={dict(request.headers)} body={request.body[:1000]}")
    # Also print to stdout for immediate debugging in dev
    try:
        print("[DEBUG] create_order_view headers:", dict(request.headers))
        print("[DEBUG] create_order_view body:", request.body[:2000])
    except Exception:
        pass

    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "error": "Invalid payload",
            "details": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    plan = serializer.validated_data['plan']
    
    if plan not in PLANS:
        return Response({
            "error": "Invalid plan",
            "available_plans": list(PLANS.keys())
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get pricing for the plan (server stores whole rupees)
    amount_rupees = PLANS[plan]
    amount_paise = int(amount_rupees * 100)

    # Create a local record first so we can reconcile if remote call fails
    with transaction.atomic():
        # Build a short receipt (Razorpay enforces max length 40)
        # Use local order id in receipt to keep it short and unique
        # We'll create the local DB record first to get the id
        
        # Create local order record first
        # Store amount in the DB as whole rupees (per request)
        rp_order = RazorpayOrder.objects.create(
            student=request.user,
            plan=plan,
            amount=amount_rupees,
            currency='INR',
            status='initiated'  # initiated -> created -> paid/failed
        )
        # Create a compact receipt using the local order id and timestamp
        receipt = f"rec_{rp_order.id}_{int(timezone.now().timestamp())}"

        try:
            # Create razorpay order
            order = create_order(
                amount_paise=amount_paise, 
                currency='INR', 
                receipt=receipt,
                notes={"plan": plan, "student_id": str(request.user.student_id), "local_order_id": str(rp_order.id)}
            )
            logger.debug(f"Razorpay create_order returned: {order}")
            print("[DEBUG] razorpay.create_order returned id:", order.get('id'))
            # Update local record with razorpay order id
            rp_order.razorpay_order_id = order.get('id')
            rp_order.status = 'created'
            rp_order.save(update_fields=['razorpay_order_id', 'status', 'updated_at'])
            
            logger.info(f"Created order {order.get('id')} for student {request.user.student_id}, plan {plan}")
            try:
                masked_key = settings.RAZORPAY_KEY_ID[:4] + '...' + settings.RAZORPAY_KEY_ID[-4:]
                print(f"[DEBUG] Returning Razorpay key_id (masked): {masked_key}")
                logger.debug(f"Returning Razorpay key_id (masked): %s", masked_key)
            except Exception:
                pass

        except Exception as exc:
            # Keep local record for retry/reconciliation
            rp_order.status = 'remote_failed'
            rp_order.save(update_fields=['status', 'updated_at'])
            logger.exception(f"Razorpay order creation failed for local order {rp_order.id}: {str(exc)}")
            print("[ERROR] Exception in create_order_view:", str(exc))

            # If Razorpay returned a BadRequestError (e.g. receipt too long), return 400 with details
            try:
                if isinstance(exc, razorpay.errors.BadRequestError):
                    return Response({
                        "error": "Invalid request to payment provider",
                        "local_order_id": rp_order.id,
                        "details": str(exc)
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                # If razorpay.errors isn't available for some reason, fall back to string match
                if 'receipt' in str(exc).lower() or 'badrequest' in str(type(exc)).lower():
                    return Response({
                        "error": "Invalid request to payment provider",
                        "local_order_id": rp_order.id,
                        "details": str(exc)
                    }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "error": "Failed to create payment order",
                "local_order_id": rp_order.id,
                "details": "Payment service temporarily unavailable"
            }, status=status.HTTP_502_BAD_GATEWAY)

        # Return amount to frontend in paise (gateway expects smallest currency unit)
        return Response({
            "order_id": rp_order.razorpay_order_id,
            "amount": amount_paise,
            "currency": rp_order.currency,
            "key_id": settings.RAZORPAY_KEY_ID,
            # Also return `key` for frontend convenience (Razorpay expects `key` in JS options)
            "key": settings.RAZORPAY_KEY_ID,
            "local_order_id": rp_order.id,
            "plan": plan
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment_view(request):
    """
    Verify payment signature and update subscription (idempotent)
    
    POST /api/payments/verify-payment/
    Body: {
        "razorpay_order_id": "...",
        "razorpay_payment_id": "...", 
        "razorpay_signature": "...",
        "local_order_id": 123
    }
    """
    # Debug incoming request
    try:
        print('[DEBUG] verify_payment_view headers:', dict(request.headers))
        print('[DEBUG] verify_payment_view body:', request.body[:2000])
    except Exception:
        pass

    serializer = VerifyPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        print('[DEBUG] verify_payment_view serializer errors:', serializer.errors)
        logger.debug('verify_payment_view serializer invalid: %s', serializer.errors)

        # Fallback: sometimes Razorpay checkout (UPI/async) returns only razorpay_payment_id
        # Try to handle case where payload includes only `razorpay_payment_id` by fetching payment
        try:
            payload = json.loads(request.body.decode('utf-8') if isinstance(request.body, (bytes, bytearray)) else request.body)
        except Exception:
            payload = {}

        if payload and 'razorpay_payment_id' in payload:
            payment_id = payload.get('razorpay_payment_id')
            print(f'[DEBUG] Fallback: fetching payment {payment_id}')
            try:
                client = get_client()
                payment = client.payment.fetch(payment_id)
                print(f'[DEBUG] Fetched payment: {payment}')
            except Exception as e:
                print(f'[ERROR] Failed to fetch payment: {str(e)}')
                logger.exception('Failed to fetch payment from Razorpay for id %s: %s', payment_id, str(e))
                return Response({
                    'error': 'Failed to fetch payment details',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

            # Payment contains order_id and status
            order_id = payment.get('order_id')
            payment_status = payment.get('status')
            payment_amount = payment.get('amount')
            payment_created_at = payment.get('created_at')
            print(f'[DEBUG] Payment order_id: {order_id}, status: {payment_status}, amount: {payment_amount}')

            if not order_id:
                print('[DEBUG] Payment has no order_id, trying to match by amount and timestamp')
                # For UPI payments, order_id might be None initially
                # Try to find the most recent local order with matching amount for this student
                try:
                    # Convert payment timestamp to Django timezone
                    from datetime import datetime
                    payment_time = datetime.fromtimestamp(payment_created_at, tz=timezone.get_current_timezone())
                    
                    # Find recent orders (within 1 hour) with matching amount
                    one_hour_ago = timezone.now() - timedelta(hours=1)

                    # `payment_amount` is in paise from Razorpay; convert to whole rupees
                    try:
                        payment_amount_rupees = int(int(payment_amount) // 100)
                    except Exception:
                        payment_amount_rupees = None

                    rp_order = RazorpayOrder.objects.filter(
                        student=request.user,
                        amount=payment_amount_rupees,
                        created_at__gte=one_hour_ago,
                        status__in=['initiated', 'created']  # Not already paid
                    ).order_by('-created_at').first()
                    
                    if not rp_order:
                        print('[ERROR] No matching local order found by amount/time')
                        return Response({
                            'error': 'Cannot match payment to order',
                            'details': f'No recent order found with amount {payment_amount} paise'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    print(f'[DEBUG] Matched payment to local order {rp_order.id} by amount/timestamp')
                    order_id = rp_order.razorpay_order_id  # Use this for logging
                    matched_order = rp_order
                    
                except Exception as e:
                    print(f'[ERROR] Error matching payment by amount: {str(e)}')
                    return Response({
                        'error': 'Failed to match payment to order',
                        'details': str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                matched_order = None  # Will be fetched later by order_id

            try:
                with transaction.atomic():
                    if matched_order:
                        # Already found by amount/timestamp matching
                        rp_order = RazorpayOrder.objects.select_for_update().get(id=matched_order.id)
                        print(f'[DEBUG] Using pre-matched order: {rp_order.id}, status: {rp_order.status}')
                    else:
                        # Find by razorpay_order_id
                        print(f'[DEBUG] Looking for local order with razorpay_order_id: {order_id}')
                        rp_order = RazorpayOrder.objects.select_for_update().get(
                            razorpay_order_id=order_id,
                            student=request.user
                        )
                        print(f'[DEBUG] Found local order: {rp_order.id}, status: {rp_order.status}')

                    # If already paid, return success
                    if rp_order.status == 'paid':
                        print('[DEBUG] Order already paid, returning success')
                        return Response({
                            'status': 'already_paid',
                            'plan': rp_order.plan,
                            'message': 'Payment already processed'
                        }, status=status.HTTP_200_OK)

                    # Only accept 'captured' status as final success. 'authorized' is not final for many payment methods (e.g. UPI)
                    if payment_status == 'captured':
                        print(f'[DEBUG] Payment captured, marking order as paid')
                        # Mark order as paid
                        rp_order.razorpay_payment_id = payment_id
                        rp_order.status = 'paid'
                        rp_order.save(update_fields=['razorpay_payment_id', 'status', 'updated_at'])

                        # Update student subscription
                        now = timezone.now()
                        expires_at = now + timedelta(days=30)
                        student = request.user
                        student.subscription_plan = rp_order.plan
                        student.subscription_expires_at = expires_at
                        student.save(update_fields=['subscription_plan', 'subscription_expires_at'])

                        logger.info('Payment fetched and verified via API; subscription updated for student %s', request.user.student_id)
                        print('[DEBUG] Subscription updated successfully')

                        return Response({
                            'status': 'success',
                            'plan': rp_order.plan,
                            'expires_at': expires_at.isoformat(),
                            'message': f'Payment verified ({payment_status}) and subscription activated'
                        }, status=status.HTTP_200_OK)
                    elif payment_status == 'authorized':
                        # Authorized indicates the payment is created but not captured. Do not mark as paid yet.
                        print(f'[DEBUG] Payment is authorized but not captured yet (payment_id={payment_id}). Returning pending.')
                        logger.info('Payment %s is authorized but not captured yet. Waiting for capture/webhook.', payment_id)
                        return Response({
                            'status': 'pending',
                            'message': 'Payment authorized but not yet captured. Please wait a moment and retry verification, or rely on webhook to finalize.'
                        }, status=202)
                    else:
                        print(f'[DEBUG] Payment not captured/authorized, status: {payment_status}')
                        # Payment exists but not captured/authorized yet
                        return Response({
                            'error': 'Payment not ready',
                            'details': f'Payment status is {payment_status}. Please retry after payment completes or wait for webhook.'
                        }, status=status.HTTP_400_BAD_REQUEST)
            except RazorpayOrder.DoesNotExist:
                print(f'[ERROR] No local order found for razorpay_order_id: {order_id}')
                return Response({
                    'error': 'Local order not found',
                    'details': f'No local order matching razorpay order {order_id} for this student'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                print(f'[ERROR] Unexpected error in fallback: {str(e)}')
                logger.exception('Unexpected error in payment fallback for payment_id %s', payment_id)
                return Response({
                    'error': 'Internal error during payment verification',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # If fallback didn't apply, return the original serializer errors
        return Response({
            "error": "Invalid payload",
            "details": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    local_order_id = data['local_order_id']

    try:
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            rp_order = RazorpayOrder.objects.select_for_update().get(
                id=local_order_id,
                student=request.user
            )
            
            # Idempotency check: if already paid, return success without re-processing
            if rp_order.status == 'paid':
                logger.info(f"Order {local_order_id} already paid, returning success")
                return Response({
                    "status": "already_paid",
                    "plan": rp_order.plan,
                    "message": f"Payment already processed for {rp_order.plan} plan"
                }, status=status.HTTP_200_OK)
            
            # Verify that the razorpay_order_id matches
            if rp_order.razorpay_order_id != data['razorpay_order_id']:
                logger.warning(f"Razorpay order ID mismatch for local order {local_order_id}")
                return Response({
                    "error": "Order ID mismatch"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify signature with Razorpay
            payment_data = {
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            }
            
            is_valid = verify_payment_signature(payment_data)

            if not is_valid:
                # Mark order as failed
                rp_order.status = 'failed'
                rp_order.save(update_fields=['status', 'updated_at'])
                
                logger.warning(f"Payment verification failed for order {local_order_id}, student {request.user.student_id}")
                
                return Response({
                    "error": "Payment verification failed",
                    "details": "Invalid signature"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Mark order as paid
            rp_order.razorpay_payment_id = data['razorpay_payment_id']
            rp_order.razorpay_signature = data['razorpay_signature']
            rp_order.status = 'paid'
            rp_order.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status', 'updated_at'])

            # Update student subscription (30 days from now)
            now = timezone.now()
            expires_at = now + timedelta(days=30)
            
            student = request.user
            student.subscription_plan = rp_order.plan
            student.subscription_expires_at = expires_at
            student.save(update_fields=['subscription_plan', 'subscription_expires_at'])

            logger.info(f"Payment verified and subscription updated for student {request.user.student_id}, plan {rp_order.plan}")

            return Response({
                "status": "success",
                "plan": rp_order.plan,
                "expires_at": expires_at.isoformat(),
                "message": f"Successfully subscribed to {rp_order.plan} plan"
            }, status=status.HTTP_200_OK)

    except RazorpayOrder.DoesNotExist:
        logger.warning(f"Order {local_order_id} not found for student {request.user.student_id}")
        return Response({
            "error": "Order not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.exception(f"Unexpected error verifying payment for local order {local_order_id}")
        return Response({
            "error": "Internal server error",
            "details": "Payment verification failed"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status_view(request):
    """
    Get current subscription status for the authenticated student
    
    GET /api/payments/subscription-status/
    """
    student = request.user
    
    # Check if subscription is active
    is_active = False
    if student.subscription_plan and student.subscription_expires_at:
        is_active = student.subscription_expires_at > timezone.now()
    
    return Response({
        "subscription_plan": student.subscription_plan,
        "subscription_expires_at": student.subscription_expires_at.isoformat() if student.subscription_expires_at else None,
        "is_active": is_active,
        "available_plans": PLANS
    }, status=status.HTTP_200_OK)