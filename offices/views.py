import requests
from django.shortcuts import render
from django.http import JsonResponse
from .services import recommend_offices, fetch_office_waiting, SERVICE_CHOICES, fetch_office_list, haversine_km


def index(request):
    offices = fetch_office_list()
    regions_set = set()
    for o in offices:
        if o.get('address'):
            parts = o.get('address').split()
            if len(parts) >= 2:
                city = parts[0][:2] if (parts[0].endswith('광역시') or parts[0].endswith('특별시') or parts[0].endswith('자치시') or parts[0].endswith('자치도')) else parts[0]
                regions_set.add(f"{city} {parts[1]}")
    
    supported_regions = sorted(list(regions_set))
    return render(request, 'offices/index.html', {
        'service_choices': SERVICE_CHOICES,
        'supported_regions': supported_regions,
    })


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


def api_check_region(request):
    try:
        lat = float(request.GET.get('lat', 0))
        lng = float(request.GET.get('lng', 0))
        
        # 1. 거리 기반 체크 (빠르고 확실한 fallback)
        offices = fetch_office_list()
        min_dist = float('inf')
        for o in offices:
            dist = haversine_km(lat, lng, o['lat'], o['lng'])
            if dist < min_dist:
                min_dist = dist
                
        # 10km 이내 민원실이 있으면 무조건 지원 지역으로 간주
        if min_dist <= 10.0:
            return JsonResponse({'supported': True, 'region': '현재 계신 지역'})
            
        # 2. Nominatim 역지오코딩 (옵션)
        # 10km 보다 멀더라도 행정구역 상 속할 수 있으므로 추가 체크
        headers = {'User-Agent': 'MinjeonApp/1.0'}
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&accept-language=ko"
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get('address', {})
            # Nominatim은 구/군을 borough, county, city 등으로 내려줌
            local_name = address.get('borough') or address.get('county') or address.get('city', '')
            
            # 사무소 목록에서 지원 지역 포함 여부 확인
            for o in offices:
                if local_name and local_name in o.get('address', ''):
                    return JsonResponse({'supported': True, 'region': local_name})
                    
        return JsonResponse({'supported': False, 'region': '알 수 없는 지역'})
    except Exception as e:
        # 에러 발생 시 일단 지원 지역으로 간주하거나, 거리 기반 결과만 믿음
        print(f"[api_check_region] Error: {e}")
        return JsonResponse({'supported': False, 'region': '오류'})
