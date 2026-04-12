import re

path = r'c:\Users\Minjun\Downloads\minjeon_project\minjeon\static\js\main.js'
with open(path, 'r', encoding='utf-8', errors='surrogateescape') as f:
    text = f.read()

# Replace getWaitingColorClass
color_logic = r'''function getWaitingColorClass(cnt) {
  if (cnt === -1) return 'gray';
  if (cnt === 0) return 'green';
  if (cnt <= 7) return 'yellow';
  return 'red';
}'''
text = re.sub(r'function getWaitingColorClass.*?return \'red\';\s*\}', color_logic, text, flags=re.DOTALL)

# Replace the inner html of renderResults
new_card = r'''
    html += `
      <div class="result-card ${isTop}">
        <div class="result-rank">
          <span class="rank-badge">${office.badge || ''}</span>
          <span class="rank-score">${office.times.total > 0 ? `총 ${office.times.total}분 소요` : '소요시간 예측 불가'}</span>
        </div>
        
        <div class="result-name">${office.name}</div>
        <div class="result-address">📌 ${office.address}</div>
        ${office.phone ? `<div class="result-phone">📞 ${office.phone}</div>` : ''}
        
        <div class="metrics">
          <div class="metric">
            <div class="metric-value ${colorClass}">${office.waiting_count === -1 ? '❌' : office.waiting_count + '명'}</div>
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
              ${office.waiting_count === -1 
                ? `<div class="score-bar" style="width: 100%; background: #e5e7eb; color: #6b7280; font-size: 0.8rem; display: flex; align-items: center; justify-content: center;">준비 중</div>`
                : `<div class="score-bar score-bar--purple" style="width: ${Math.min(100, Math.round((office.times.waiting / 60) * 100))}%"></div>`
              }
            </div>
            <span class="score-num">${office.waiting_count === -1 ? '-' : office.times.waiting + '분'}</span>
          </div>
        </div>
        
        <a class="btn-map" href="https://map.kakao.com/link/map/${encodeURIComponent(office.name)},${office.lat},${office.lng}" target="_blank">
          🗺️ 카카오맵 길찾기
        </a>
      </div>
    `;
'''

text = re.sub(r'html \+= `\s*<div class="result-card.*?</div\>\s*`;', new_card.strip(), text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
    f.write(text)

print("Updated main.js")
