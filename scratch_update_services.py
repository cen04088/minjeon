import re

path = r'c:\Users\Minjun\Downloads\minjeon_project\minjeon\offices\services.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# We completely rewrite the bottom part of services.py starting from recommend_offices
# using regex or just splitting the file up to line 160.
# Actually, let's just replace the recommend_offices function and SERVICE_CHOICES block.

new_logic = '''
def search_kakao_local_offices(user_lat, user_lng, query):
    api_key = getattr(settings, 'KAKAO_REST_API_KEY', '')
    if not api_key:
        return []
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "query": query,
        "x": user_lng,
        "y": user_lat,
        "radius": 10000,
        "sort": "distance"
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=3)
        if resp.status_code == 200:
            return resp.json().get('documents', [])
    except Exception as e:
        print("[Kakao Local Search Error]", e)
    return []

# 업무별 실제 데이터 taskNm 키워드 매핑
API_TASK_MAPPING = {
    '출생, 사망 신고': ['출생', '사망'],
    '혼인, 이혼 신고': ['혼인', '이혼'],
    '등본, 인감, 가족관계 증명서': ['등본', '인감', '가족관계'],
    '체류지 변경(전입신고)': ['체류지변경'],
    '인감 등록': ['인감'],
    '부동산 거래 신고': ['부동산거래 신고'],
    '차량 취득세': ['차량 취득세'],
    '여권': ['여권'],
}

def recommend_offices_prediction(
    user_lat: float,
    user_lng: float,
    selected_service: str = '',
    top_n: int = 3,
) -> list:
    """예측 모드 (41개 지자체 한정)"""
    offices     = fetch_office_list()
    waiting_all = fetch_all_waiting()
    results     = []
    now = datetime.now()
    
    for office in offices:
        cso_id      = office['id']
        waiting_map = waiting_all.get(cso_id, {})

        if selected_service and waiting_map:
            kws = API_TASK_MAPPING.get(selected_service, [selected_service])
            if not any(any(kw in nm for kw in kws) for nm in waiting_map.keys()):
                continue
            waiting_count = 0
            for nm, cnt in waiting_map.items():
                if any(kw in nm for kw in kws):
                    waiting_count += cnt
        else:
            waiting_count = sum(waiting_map.values()) if waiting_map else 0

        expected_wait_min = waiting_count * 3 
        distance_km = haversine_km(user_lat, user_lng, office['lat'], office['lng'])
        if distance_km > 30.0:
            continue
            
        try:
            h, m = map(int, office['close_time'].split(':'))
            close = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if office['night_open'] and now.hour >= 18:
                close = now.replace(hour=20, minute=0, second=0, microsecond=0)
            remain_min = (close - now).total_seconds() / 60
        except:
            remain_min = 1000
            
        if remain_min <= 0:
            continue

        driving_time_min = get_driving_time(user_lat, user_lng, office['lat'], office['lng'])
        total_time_min = driving_time_min + expected_wait_min

        results.append({
            'mode': 'PREDICTION',
            'id':             cso_id,
            'name':           office['name'],
            'address':        office['address'],
            'phone':          office['phone'],
            'lat':            office['lat'],
            'lng':            office['lng'],
            'distance_km':    round(distance_km, 1),
            'waiting_count':  waiting_count,
            'waiting_label':  _waiting_label(waiting_count),
            'available_tasks': list(waiting_map.keys()),
            'close_time':     office['close_time'],
            'night_open':     office['night_open'],
            'night_desc':     office['night_desc'],
            'times': {
                'driving':  round(driving_time_min),
                'waiting':  expected_wait_min,
                'total':    round(total_time_min),
            },
        })

    results.sort(key=lambda x: x['times']['total'])
    top = results[:top_n]
    badges = ['🏆 최적 추천(최단시간)', '✅ 2순위', '📍 3순위']
    for i, r in enumerate(top):
        r['rank']        = i + 1
        r['badge']       = badges[i] if i < len(badges) else ''
        r['tomorrow']    = False

    return top

def recommend_offices_general(
    user_lat: float,
    user_lng: float,
    selected_service: str = '',
    top_n: int = 3,
) -> list:
    """일반 모드 (전국 대상, 카카오 로컬 검색)"""
    # 서비스 분류에 따른 검색 키워드 타겟팅
    is_city_hall = False
    if selected_service in SERVICE_CHOICES['시·구청 가능 업무']:
        is_city_hall = True

    results = []
    
    if is_city_hall:
        docs = search_kakao_local_offices(user_lat, user_lng, '구청')
        if not docs:
            docs = search_kakao_local_offices(user_lat, user_lng, '시청')
        # 거리가 가까운 순으로 합치기
        # 카카오 api sort=distance 자체가 정렬을 해줌
    else:
        docs = search_kakao_local_offices(user_lat, user_lng, '행정복지센터')
        
    for i, doc in enumerate(docs[:top_n]):
        dest_lat = float(doc.get('y', 0))
        dest_lng = float(doc.get('x', 0))
        dist_m = int(doc.get('distance', 0))
        dist_km = dist_m / 1000.0
        
        driving_time_min = get_driving_time(user_lat, user_lng, dest_lat, dest_lng)
        
        results.append({
            'mode': 'GENERAL',
            'id':             doc.get('id'),
            'name':           doc.get('place_name'),
            'address':        doc.get('road_address_name') or doc.get('address_name'),
            'phone':          doc.get('phone', ''),
            'lat':            dest_lat,
            'lng':            dest_lng,
            'distance_km':    round(dist_km, 1),
            'waiting_count':  -1, # 준비중
            'waiting_label':  '알 수 없음 ⚪',
            'available_tasks': [selected_service],
            'close_time':     '18:00',
            'night_open':     False,
            'night_desc':     '',
            'times': {
                'driving':  round(driving_time_min),
                'waiting':  0,
                'total':    round(driving_time_min),
            },
        })
        
    results.sort(key=lambda x: x['times']['total'])
    badges = ['🏆 가장 가까움', '✅ 2순위', '📍 3순위']
    for i, r in enumerate(results):
        r['rank']        = i + 1
        r['badge']       = badges[i] if i < len(badges) else ''
        r['tomorrow']    = False

    return results

def fetch_office_waiting(cso_sn: str) -> dict:
    try:
        items = _fetch_all_pages(settings.WAITING_API_URL, {'csoSn': cso_sn})
        return {item.get('taskNm', '기타'): int(item.get('wtngCnt', 0) or 0)
                for item in items}
    except Exception as e:
        print(f"[fetch_office_waiting] {cso_sn} Error: {e}")
        return {}

SERVICE_CHOICES = {
    '동사무소(행정복지센터) 가능 업무': [
        '출생, 사망 신고',
        '등본, 인감, 가족관계 증명서',
        '체류지 변경(전입신고)',
        '인감 등록',
    ],
    '시·구청 가능 업무': [
        '혼인, 이혼 신고',
        '부동산 거래 신고',
        '차량 취득세',
        '여권',
    ]
}

def _mock_offices():
    return [
        {'id': 'CS0001', 'name': '광진구청',   'address': '서울특별시 광진구 아차산로 400',    'lat': 37.536399, 'lng': 127.088006, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 목요일 20시까지', 'phone': ''},
        {'id': 'CS0002', 'name': '마포구청',   'address': '서울 마포구 월드컵로 212',          'lat': 37.566387, 'lng': 126.901942, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 월요일 20시까지', 'phone': ''},
        {'id': 'CS0005', 'name': '서초구청',   'address': '서울 서초구 남부순환로 2584',        'lat': 37.483597, 'lng': 127.032699, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 수요일 20시까지', 'phone': ''},
        {'id': 'CS0004', 'name': '영등포구청', 'address': '서울 영등포구 당산로 123',           'lat': 37.526273, 'lng': 126.895956, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 화요일 20시까지', 'phone': ''},
        {'id': 'CS0006', 'name': '강동구청',   'address': '서울 강동구 성내로 25',             'lat': 37.530134, 'lng': 127.123746, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 화요일 20시까지', 'phone': ''},
        {'id': 'CS0003', 'name': '금천구청',   'address': '서울 금천구 시흥대로73길 70',        'lat': 37.456778, 'lng': 126.895403, 'open_time': '09:00', 'close_time': '18:00', 'night_open': True,  'night_desc': '매주 목요일 20시까지', 'phone': ''},
    ]
'''

# We will cut the file at `def recommend_offices(` and append new_logic
pattern = re.compile(r'def recommend_offices\(.*', re.DOTALL)
new_text = pattern.sub(new_logic, text)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Updated services.py")
