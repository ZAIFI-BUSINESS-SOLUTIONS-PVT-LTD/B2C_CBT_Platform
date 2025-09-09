from django.http import JsonResponse
from celery.result import AsyncResult
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def task_status(request, task_id: str):
    """Return Celery task status and result for a given task_id."""
    res = AsyncResult(task_id)
    payload = {
        'task_id': task_id,
        'status': res.status,
        'ready': res.ready(),
        'result': None,
        'traceback': None,
    }
    if res.ready():
        try:
            payload['result'] = res.result
        except Exception:
            payload['result'] = str(res.result)
    if res.failed():
        payload['traceback'] = res.traceback
    return JsonResponse(payload)
