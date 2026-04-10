from django.shortcuts import render
from django.http import JsonResponse
from .services import recommend_offices, fetch_office_waiting, SERVICE_CHOICES


def index(request):
    return render(request, 'offices/index.html', {'service_choices': SERVICE_CHOICES})


def recommend(request):
    try:
        lat     = float(request.GET.get('lat', 0))
        lng     = float(request.GET.get('lng', 0))
        service = request.GET.get('service', '')
        mode    = request.GET.get('mode', 'SMART')

        if not lat or not lng:
            return render(request, 'offices/index.html', {
                'error': '위치 정보를 가져올 수 없습니다. 위치 권한을 허용해 주세요.',
                'service_choices': SERVICE_CHOICES,
            })

        results = recommend_offices(lat, lng, service, mode)
        return render(request, 'offices/result.html', {
            'results':          results,
            'selected_service': service or '전체',
            'mode':             mode,
            'user_lat':         lat,
            'user_lng':         lng,
        })
    except Exception as e:
        return render(request, 'offices/index.html', {
            'error': f'오류가 발생했습니다: {str(e)}',
            'service_choices': SERVICE_CHOICES,
        })


def api_recommend(request):
    """GET /api/recommend/?lat=&lng=&service=&mode= → JSON"""
    try:
        lat     = float(request.GET.get('lat', 0))
        lng     = float(request.GET.get('lng', 0))
        service = request.GET.get('service', '')
        mode    = request.GET.get('mode', 'SMART')
        results = recommend_offices(lat, lng, service, mode)
        return JsonResponse({'status': 'ok', 'data': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def api_waiting(request):
    """GET /api/waiting/?cso_sn=CS0001 → 특정 민원실 실시간 대기현황 JSON"""
    cso_sn = request.GET.get('cso_sn', '')
    if not cso_sn:
        return JsonResponse({'status': 'error', 'message': 'cso_sn 파라미터 필요'}, status=400)
    data = fetch_office_waiting(cso_sn)
    return JsonResponse({'status': 'ok', 'office_id': cso_sn, 'waiting': data})
