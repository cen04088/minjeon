import requests
from django.shortcuts import render
from django.http import JsonResponse
from .services import recommend_offices_general, recommend_offices_prediction, fetch_office_waiting, SERVICE_CHOICES, GENERAL_SERVICE_CHOICES, fetch_office_list, haversine_km


def index(request):
    # 41개 서비스 지역 하드코딩 (API 타임아웃에 무관하게 항상 표시)
    KNOWN_REGIONS = {
        '서울': ['강남구', '강동구', '광진구', '금천구', '마포구', '서초구', '영등포구'],
        '부산': ['부산진구', '해운대구'],
        '대구': ['달서구', '수성구'],
        '인천': ['남동구', '연수구', '부평구'],
        '광주': ['광산구', '북구', '서구'],
        '대전': ['서구', '유성구'],
        '울산': ['남구', '울주군'],
        '경기도': ['고양시', '남양주시', '성남시', '수원시', '안산시', '용인시', '화성시'],
        '강원도': ['원주시', '춘천시'],
        '충청북도': ['청주시'],
        '충청남도': ['아산시', '천안시'],
        '전라북도': ['전주시'],
        '전라남도': ['순천시', '여수시'],
        '경상북도': ['경주시', '구미시', '포항시'],
        '경상남도': ['김해시', '창원시'],
        '제주': ['제주시'],
    }
    total_offices = 42
    grouped_regions = {prov: sorted(cities) for prov, cities in sorted(KNOWN_REGIONS.items())}

    return render(request, 'offices/index.html', {
        'service_choices':            GENERAL_SERVICE_CHOICES,
        'prediction_service_choices': SERVICE_CHOICES,
        'grouped_regions': grouped_regions,
        'total_offices': total_offices,
    })



def recommend(request):
    try:
        lat         = float(request.GET.get('lat', 0))
        lng         = float(request.GET.get('lng', 0))
        service     = request.GET.get('service', '')
        search_mode = request.GET.get('search_mode', 'GENERAL')
        transport_mode = request.GET.get('transport_mode', 'driving')
        debug_mode  = request.GET.get('debug_mode', '0') == '1'
        fallback_msg = None

        if not lat or not lng:
            return render(request, 'offices/index.html', {
                'error': '위치 정보를 가져올 수 없습니다. 위치 권한을 허용해 주세요.',
                'service_choices': SERVICE_CHOICES,
            })

        if search_mode == 'PREDICTION':
            results = recommend_offices_prediction(lat, lng, service, transport_mode=transport_mode, debug_mode=debug_mode)
            if not results:
                results = recommend_offices_general(lat, lng, service, transport_mode=transport_mode)
                search_mode = 'GENERAL'
                fallback_msg = "실시간 대기현황 데이터가 없는 지역이거나 서버 오류로 인해, '일반 모드' 검색 결과로 자동 전환되었습니다."
        else:
            results = recommend_offices_general(lat, lng, service, transport_mode=transport_mode)

        return render(request, 'offices/result.html', {
            'results':          results,
            'selected_service': service,
            'search_mode':      search_mode,
            'fallback_msg':     fallback_msg,
            'user_lat':         lat,
            'user_lng':         lng,
            'debug_mode':       debug_mode,
        })
    except Exception as e:
        return render(request, 'offices/index.html', {
            'error': f'오류가 발생했습니다: {str(e)}',
            'service_choices': SERVICE_CHOICES,
        })


def api_recommend(request):
    """GET /api/recommend/?lat=&lng=&service=&search_mode=&debug_mode= → JSON"""
    try:
        lat         = float(request.GET.get('lat', 0))
        lng         = float(request.GET.get('lng', 0))
        service     = request.GET.get('service', '')
        search_mode = request.GET.get('search_mode', 'GENERAL')
        transport_mode = request.GET.get('transport_mode', 'driving')
        debug_mode  = request.GET.get('debug_mode', '0') == '1'
        fallback_msg = None
        
        if search_mode == 'PREDICTION':
            results = recommend_offices_prediction(lat, lng, service, transport_mode=transport_mode, debug_mode=debug_mode)
            if not results:
                results = recommend_offices_general(lat, lng, service, transport_mode=transport_mode)
                search_mode = 'GENERAL'
                fallback_msg = "예측 모드 데이터가 없어 일반 모드로 전환되었습니다."
        else:
            results = recommend_offices_general(lat, lng, service, transport_mode=transport_mode)
            
        return JsonResponse({
            'status': 'ok', 
            'data': results, 
            'search_mode': search_mode,
            'fallback_msg': fallback_msg
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
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
    # 예측 모드 지원 지역 목록 (views.py의 KNOWN_REGIONS와 동일)
    SUPPORTED_KEYWORDS = {
        # 서울 자치구
        '강남구', '강동구', '광진구', '금천구', '마포구', '서초구', '영등포구',
        # 부산
        '부산진구', '해운대구',
        # 대구
        '달서구', '수성구',
        # 인천
        '남동구', '연수구', '부평구',
        # 광주
        '광산구', '북구', '서구',
        # 대전
        '유성구',
        # 울산
        '남구', '울주군',
        # 경기도
        '고양시', '남양주시', '성남시', '수원시', '안산시', '용인시', '화성시',
        # 강원도
        '원주시', '춘천시',
        # 충청북도/남도
        '청주시', '아산시', '천안시',
        # 전라북도/남도
        '전주시', '순천시', '여수시',
        # 경상북도/남도
        '경주시', '구미시', '포항시', '김해시', '창원시',
        # 제주
        '제주시',
    }
    # 대전 서구는 광주 서구와 겹치므로 도 이름으로 추가 구분
    DAEJEON_SUPPORTED = {'서구'}  # 대전광역시 서구

    try:
        lat = float(request.GET.get('lat', 0))
        lng = float(request.GET.get('lng', 0))

        from django.core.cache import cache
        from django.conf import settings
        cache_key = f"region_kakao_{round(lat, 3)}_{round(lng, 3)}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return JsonResponse(cached_data)

        region_name = '알 수 없는 지역'
        is_supported = False

        api_key = getattr(settings, 'KAKAO_REST_API_KEY', '')
        if api_key:
            url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
            headers = {"Authorization": f"KakaoAK {api_key}"}
            params = {"x": lng, "y": lat}
            resp = requests.get(url, headers=headers, params=params, timeout=4)
            if resp.status_code == 200:
                docs = resp.json().get('documents', [])
                if docs:
                    doc = docs[0]
                    # 시군구 (예: 강남구)
                    city_district = doc.get('region_2depth_name', '')
                    # 읍면동 (예: 역삼동)
                    dong = doc.get('region_3depth_name', '')
                    
                    region_name = dong if dong else city_district

                    # 지원 여부 판단
                    for keyword in SUPPORTED_KEYWORDS:
                        sido = doc.get('region_1depth_name', '')
                        if keyword in city_district or keyword in sido:
                            # 대전광역시 / 광주광역시의 서구만 인정
                            if keyword == '서구' and '대전' not in sido and '광주' not in sido:
                                continue
                            is_supported = True
                            break

        result = {'supported': is_supported, 'region': region_name}
        cache.set(cache_key, result, 3600)
        return JsonResponse(result)

    except Exception as e:
        print(f"[api_check_region] Error: {e}")
        return JsonResponse({'supported': False, 'region': '확인 불가'})


import json
import os
from django.views.decorators.csrf import csrf_exempt

def api_search_location(request):
    """GET /api/search_location/?q=키워드"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'status': 'error', 'message': '검색어를 입력해주세요'}, status=400)
        
    from .services import search_kakao_location
    result = search_kakao_location(query)
    if result:
        return JsonResponse({'status': 'ok', 'data': result})
    else:
        return JsonResponse({'status': 'error', 'message': '검색 결과를 찾을 수 없습니다.'}, status=404)


@csrf_exempt
def api_chat(request):
    """POST /api/chat/ → LLM (Gemini 2.5 Flash Lite) 응답"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '')
        
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return JsonResponse({'reply': '서버에 GEMINI_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요.'})
        
        system_prompt = """# Role & Persona
당신은 대한민국 관공서 민원 처리를 돕는 전문적이고 친절한 AI 어시스턴트 '민원ON 도우미'입니다.
사용자가 특정 민원(예: 여권 발급, 전입신고, 인감증명서 발급 등)을 언급하면, 관공서 방문 전에 미리 준비해야 할 필수 서류와 정보를 정확하고 보기 쉽게 안내해야 합니다.

# Core Objective
주요 목표는 사용자가 서류 누락으로 인해 민원실을 두 번 방문하는 일(헛걸음)이 없도록 사전에 완벽한 정보를 제공하는 것입니다.

# Output Format (반드시 아래의 마크다운 형식을 지켜서 답변할 것)
### 📄 [민원 업무명] 준비물 안내
* **필수 서류**: [해당 민원에 꼭 필요한 준비물 나열 (예: 신분증 원본, 6개월 이내 촬영한 여권용 사진 등)]
* **예상 수수료**: [발급 비용 기재. 현금/카드 가능 여부 포함]
* **처리 소요 시간**: [즉시 발급인지, 며칠 소요되는지 기재]
* **💡 민원ON 꿀팁**: [대리인 방문 시 추가 서류, 무인민원발급기 가능 여부, 주의사항 등 실질적인 팁 1~2가지]

# Guidelines & Constraints
1. **정확성과 최신화**: 대한민국 행정안전부 및 정부24 기준의 최신 정보를 바탕으로 답변하세요. 불확실한 정보라면 "정확한 확인을 위해 해당 지자체 민원실 전화 문의를 권장합니다"라고 덧붙이세요.
2. **간결성**: 사용자는 모바일 기기에서 바쁘게 정보를 확인 중입니다. 불필요한 인사말이나 서론은 생략하고 곧바로 핵심(준비물)만 출력하세요.
3. **조건부 안내**: 본인 방문 시와 대리인 방문 시 준비물이 다를 경우, 직관적으로 구분하여 설명하세요. (예: "- 본인 방문 시: ... / - 대리인 방문 시: ...")
4. **민원 외 질문 차단**: 사용자가 민원, 행정, 관공서 업무와 무관한 질문(예: 날씨, 일상 대화, 코딩 질문 등)을 할 경우, "저는 민원 서류 안내 서비스입니다. 관공서 업무와 관련된 질문을 남겨주시면 친절히 안내해 드리겠습니다."라고 단호히 거절하세요.
5. **질문 유도**: 사용자의 입력이 너무 짧거나 모호한 경우(예: "등본", "여권"), "주민등록등본 발급 준비물을 안내해 드릴까요?" 혹은 "여권 신규 발급인가요, 재발급인가요?"라고 구체적인 목적을 되물어보세요."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp_json = resp.json()
        
        # fallback to 1.5-flash if 2.5-flash-lite gives 404
        if resp.status_code == 404:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp_json = resp.json()
            
        if 'candidates' in resp_json and len(resp_json['candidates']) > 0:
            reply = resp_json['candidates'][0]['content']['parts'][0]['text']
        else:
            reply = "AI 응답을 가져오는데 실패했습니다: " + str(resp_json)
            
        return JsonResponse({'reply': reply})
        
    except Exception as e:
        print("[Gemini API Error]", str(e))
        return JsonResponse({'error': f'서버 오류가 발생했습니다: {str(e)}'}, status=500)
