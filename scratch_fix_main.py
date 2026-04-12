import re

path = r'c:\Users\Minjun\Downloads\minjeon_project\minjeon\static\js\main.js'
with open(path, 'r', encoding='utf-8', errors='surrogateescape') as f:
    text = f.read()

new_func = r'''function renderResults(results) {
  const container = document.getElementById('resultContainer');
  if (!container) return;
  
  if (!results || results.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🏛️</div>
        <p>조건에 맞는 민원실을 찾지 못했습니다.</p>
        <p>업무 종류를 변경하거나 나중에 다시 시도해 주세요.</p>
      </div>
    `;
    return;
  }
  
  let html = `<div class="result-header" style="margin-top: 24px;">
    <h2 class="result-title">추천 민원실 TOP ${results.length}</h2>
    <p class="result-sub">실시간 대기현황 기준 · 방금 전 업데이트</p>
  </div>`;
  
  if (results[0].tomorrow) {
    html += `
    <div class="alert alert-tomorrow">
      🌅 현재 운영 중인 민원실이 없습니다. <strong>내일 기준</strong> 추천 결과를 보여드려요.
    </div>`;
  }
  
  results.forEach(office => {
    const isTop = office.rank === 1 ? 'result-card--top' : '';
    const colorClass = getWaitingColorClass(office.waiting_count);
    
    html += `
      <div class="result-card ${isTop}">
        <div class="result-rank">
          <span class="rank-badge">${office.badge || ''}</span>
          <span class="rank-score">총 ${office.times.total}분 소요</span>
        </div>
        
        <div class="result-name">${office.name}</div>
        <div class="result-address">📌 ${office.address}</div>
        ${office.phone ? `<div class="result-phone">📞 ${office.phone}</div>` : ''}
        
        <div class="metrics">
          <div class="metric">
            <div class="metric-value ${colorClass}">${office.waiting_count}명</div>
            <div class="metric-label">현재 대기</div>
          </div>
          <div class="metric">
            <div class="metric-value">${office.distance_km}km</div>
            <div class="metric-label">거리</div>
          </div>
          <div class="metric">
            <div class="metric-value">~${office.close_time}</div>
            <div class="metric-label">운영 종료</div>
          </div>
        </div>
        
        <div class="waiting-label">${office.waiting_label}</div>
        
        <div class="score-bars" style="margin-top: 15px;">
          <div class="score-row">
            <span class="score-label">🚗 카카오내비 이동</span>
            <div class="score-bar-wrap">
              <div class="score-bar score-bar--blue" style="width: ${Math.min(100, Math.round((office.times.driving / 60) * 100))}%"></div>
            </div>
            <span class="score-num">${office.times.driving}분</span>
          </div>
          <div class="score-row">
            <span class="score-label">👥 예상 대기현황</span>
            <div class="score-bar-wrap">
              <div class="score-bar score-bar--purple" style="width: ${Math.min(100, Math.round((office.times.waiting / 60) * 100))}%"></div>
            </div>
            <span class="score-num">${office.times.waiting}분</span>
          </div>
        </div>
        
        <a class="btn-map" href="https://map.kakao.com/link/map/${encodeURIComponent(office.name)},${office.lat},${office.lng}" target="_blank">
          🗺️ 카카오맵 길찾기
        </a>
      </div>
    `;
  });
  
  container.innerHTML = html;
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}'''

pattern = re.compile(r'function renderResults\(results\) \{.*?\n\}\n(?=\n// PWA Service Worker Registration)', re.DOTALL)
new_text = pattern.sub(new_func, text)

with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
    f.write(new_text)

print('Updated successfully. Match found:', bool(pattern.search(text)))
