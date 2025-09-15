from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['GET', 'POST', 'OPTIONS'])
def debug_echo(request):
    """Temporary debug endpoint that echoes headers and body for reproducing client requests.

    WARNING: This endpoint is for local debugging only. Do not deploy in production.
    """
    try:
        headers = {k: v for k, v in request.headers.items()}
        body = None
        try:
            body = request.body.decode('utf-8')
        except Exception:
            body = str(request.body[:1000])

        logger.debug("debug_echo called headers=%s body=%s", headers, body[:1000] if body else None)
        print("[DEBUG] debug_echo headers:", headers)
        print("[DEBUG] debug_echo body:", body[:2000] if body else None)

        return Response({
            "headers": headers,
            "body": body
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("debug_echo error: %s", str(e))
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
