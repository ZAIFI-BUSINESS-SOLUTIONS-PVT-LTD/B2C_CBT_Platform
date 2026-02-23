from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def insights_cache(request):
    """Compatibility endpoint for `/api/insights/cache/`.
    Returns a safe, minimal insights payload so frontend doesn't get 404s.
    """
    payload = {
        "status": "ok",
        "data": {
            "strengthTopics": [],
            "weakTopics": [],
            "improvementTopics": [],
            "llmInsights": {},
            "summary": {
                "totalTopicsAnalyzed": 0,
                "totalTestsTaken": 0,
                "strengthsCount": 0,
                "weaknessesCount": 0,
                "improvementsCount": 0,
            },
            "cached": False,
            "thresholdsUsed": None,
        },
        "cacheInfo": {
            "fileExists": False,
            "fileSize": 0,
            "lastModified": None,
        },
        "cached": False,
    }
    return Response(payload)
