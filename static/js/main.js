/* main.js — GPS 위치 감지 + 폼 제출 */



function getLocation() {

  const statusEl = document.getElementById('locationStatus');

  const textEl   = document.getElementById('locationText');

  const submitBtn = document.getElementById('submitBtn');



  if (!statusEl) return;  // result 페이지에서는 실행 안 함



  textEl.textContent = '위치를 가져오는 중...';

  statusEl.querySelector('.dot').className = 'dot dot-gray';



  if (!navigator.geolocation) {

    textEl.textContent = '위치 서비스를 지원하지 않는 브라우저입니다';

    statusEl.querySelector('.dot').className = 'dot dot-red';

    return;

  }



  navigator.geolocation.getCurrentPosition(

    (pos) => {

      const lat = pos.coords.latitude.toFixed(6);

      const lng = pos.coords.longitude.toFixed(6);



      document.getElementById('lat').value = lat;

      document.getElementById('lng').value = lng;



      // 지원 지역 여부 확인

      fetch(`/api/check_region/?lat=${lat}&lng=${lng}`)

        .then(res => res.json())

        .then(data => {

          

          const predRadio = document.querySelector('input[name="search_mode"][value="PREDICTION"]');

          const genRadio = document.querySelector('input[name="search_mode"][value="GENERAL"]');

          if (data.supported) {

            textEl.innerHTML = `위치 감지 완료 (${data.region} - <span style="color: #22c55e; font-weight: 600;">일반, 예측 모드 가능</span>)`;

            statusEl.querySelector('.dot').className = 'dot dot-green';

            if (predRadio) {

                predRadio.disabled = false;

                const chip = predRadio.closest('.mode-chip');

                if (chip) { chip.style.opacity = '1'; chip.style.cursor = 'pointer'; }

            }

          } else {

            const regionText = data.region && data.region !== '알 수 없는 지역' ? `${data.region}` : '알 수 없는 지역';

            textEl.innerHTML = `위치 감지 완료 (${regionText} - <span style="color: #f59e0b; font-weight: 600;">일반 모드 가능</span>)`;

            statusEl.querySelector('.dot').className = 'dot dot-yellow';

            

            if (predRadio) {

                predRadio.disabled = false;

                const chip = predRadio.closest('.mode-chip');

                if (chip) { chip.style.opacity = '1'; chip.style.cursor = 'pointer'; }

            }

            if (genRadio) genRadio.checked = true;



            // 불가능한 지역일 경우 스마트 스코어링 빼고 추가 신청 버튼



            const card = document.getElementById('smartScoringCard');



            if (card) {



              card.innerHTML = `



                <div class="info-icon">📝</div>



                <div class="info-text" style="width: 100%;">



                  <strong>우리 동네 추가 신청</strong>



                  <span>해당 지역은 현재 서비스 준비 중입니다.</span>



                  <button type="button" class="btn-outline" style="margin-top: 8px; width: 100%; font-size: 0.9rem;" onclick="alert('신청이 완료되었습니다.')">추가 신청</button>



                </div>



              `;



            }



          }



          if (submitBtn) submitBtn.disabled = false;



        })

        .catch(err => {

          textEl.textContent = `위치 감지 완료 (${lat}, ${lng})`;

          statusEl.querySelector('.dot').className = 'dot dot-green';

          if (submitBtn) submitBtn.disabled = false;

        });

    },

    (err) => {

      textEl.textContent = '위치 권한이 거부되었습니다. 수동으로 입력해 주세요.';

      statusEl.querySelector('.dot').className = 'dot dot-red';

      // 위치 권한 없어도 서울시청 기본값으로 허용

      document.getElementById('lat').value = '37.5665';

      document.getElementById('lng').value = '126.9780';

      if (submitBtn) submitBtn.disabled = false;

    },

    { timeout: 8000, maximumAge: 60000 }

  );

}



document.addEventListener('DOMContentLoaded', () => {

  const form = document.getElementById('searchForm');

  // 모드 전환 시 서비스 패널 토글
  const modeRadios = document.querySelectorAll('input[name="search_mode"]');
  modeRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      const isPrediction = radio.value === 'PREDICTION' && radio.checked;
      const generalPanel = document.getElementById('generalServicePanel');
      const predPanel = document.getElementById('predictionServicePanel');
      if (generalPanel) generalPanel.style.display = isPrediction ? 'none' : 'block';
      if (predPanel) predPanel.style.display = isPrediction ? 'block' : 'none';
    });
  });

  if (form) {

    form.addEventListener('submit', async (e) => {

      e.preventDefault();

      const btn = document.getElementById('submitBtn');

      const originalText = btn.innerHTML;

      btn.innerHTML = '⏳ 추천 중...';

      btn.disabled = true;

      const fd = new FormData(form);

      // 예측 모드일 때 service_pred 값을 service로 변환
      const mode = fd.get('search_mode');
      if (mode === 'PREDICTION') {
        const predService = fd.get('service_pred');
        if (predService) {
          fd.set('service', predService);
        }
        fd.delete('service_pred');
      }

      const params = new URLSearchParams(fd).toString();

      try {

        const res = await fetch(`/api/recommend/?${params}`);

        const json = await res.json();

        if (json.status === 'ok') {
          renderResults(json.data, json.fallback_msg);
          // 숨기기 처리 (info-cards)

          const infoCards = document.querySelector('.info-cards');

          if (infoCards) infoCards.style.display = 'none';

        } else {

          alert('오류가 발생했습니다: ' + json.message);

        }

      } catch (err) {

        alert('네트워크 오류가 발생했습니다.');

      } finally {

        btn.innerHTML = originalText;

        btn.disabled = false;

      }

    });

  }

});



function getWaitingColorClass(cnt) {
  if (cnt === -1) return 'gray';
  if (cnt === 0) return 'green';
  if (cnt <= 7) return 'yellow';
  return 'red';
}



function renderResults(results, fallbackMsg = null) {

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

  if (fallbackMsg) {
    html += `
    <div class="alert alert-info" style="margin-bottom: 20px; border-left: 4px solid #3b82f6; background-color: #eff6ff; color: #1e40af; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; line-height: 1.5;">
      💡 <strong>안내:</strong> ${fallbackMsg}
    </div>`;
  }

  

  if (results[0].tomorrow) {

    html += `

    <div class="alert alert-tomorrow">

      🌅 현재 운영 중인 민원실이 없습니다. <strong>내일 기준</strong> 추천 결과를 보여드려요.

    </div>`;

  } else if (results[0].waiting_count >= 15) {

    html += `
    <div class="alert alert-info" style="margin-bottom: 20px; border-left: 4px solid #10b981; background-color: #ecfdf5; color: #047857; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; line-height: 1.5;">
      💡 <strong>시간 절약 꿀팁:</strong> 현재 가장 빠른 곳도 대기인원이 15명 이상으로 혼잡합니다. 급한 업무가 아니라면 <strong>오후 시간대나 내일 오전</strong>에 방문하시면 대기 시간을 아낄 수 있어요!
    </div>`;
  }

  

  results.forEach(office => {

    const isTop = office.rank === 1 ? 'result-card--top' : '';

    const colorClass = getWaitingColorClass(office.waiting_count);

    

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
            <div class="metric-value ${colorClass}">${office.waiting_count === -1 ? '준비중' : office.waiting_count + '명'}</div>
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
        
        ${office.waiting_count === -1 ? '' : `<div class="waiting-label">${office.waiting_label}</div>`}
        
        <div class="score-bars" style="margin-top: 15px;">
          <div class="score-row">
            <span class="score-label">🚗 카카오내비 이동</span>
            <div class="score-bar-wrap">
              <div class="score-bar score-bar--blue" style="width: ${Math.min(100, Math.round((office.times.driving / 60) * 100))}%"></div>
            </div>
            <span class="score-num">${office.times.driving}분</span>
          </div>
          <div class="score-row">
            <span class="score-label">🚶 도보 이동</span>
            <div class="score-bar-wrap">
              <div class="score-bar" style="background:#10b981; width: ${Math.min(100, Math.round((office.times.walking / 120) * 100))}%"></div>
            </div>
            <span class="score-num">${office.times.walking}분</span>
          </div>
          <div class="score-row">
            <span class="score-label">🚌 대중교통</span>
            <div class="score-bar-wrap">
              <div class="score-bar" style="background:#f59e0b; width: ${Math.min(100, Math.round((office.times.transit / 90) * 100))}%"></div>
            </div>
            <span class="score-num">${office.times.transit}분</span>
          </div>
          <div class="score-row">
            <span class="score-label">👥 예상 대기현황</span>
            ${office.waiting_count === -1
              ? `<span style="color: #9ca3af; font-size: 0.85rem; margin-left: 8px;">준비 중</span>`
              : `<div class="score-bar-wrap">
                  <div class="score-bar score-bar--purple" style="width: ${Math.min(100, Math.round((office.times.waiting / 60) * 100))}%"></div>
                </div>`
            }
            <span class="score-num">${office.waiting_count === -1 ? '' : office.times.waiting + '분'}</span>
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

}

// PWA Service Worker Registration

if ('serviceWorker' in navigator) {

  window.addEventListener('load', () => {

    navigator.serviceWorker.register('/static/sw.js')

      .then(registration => {

        console.log('ServiceWorker registration successful with scope: ', registration.scope);

      }, err => {

        console.log('ServiceWorker registration failed: ', err);

      });

  });

}

function setAiInput(msg) {
  const inputEl = document.getElementById("aiInput");
  if (inputEl) {
    inputEl.value = msg;
    askAI();
  }
}



async function askAI() {

  const inputEl = document.getElementById("aiInput");

  const chatBox = document.getElementById("aiChatBox");

  const msg = inputEl.value.trim();

  

  if (!msg) return;

  

  // Show chat box if hidden

  chatBox.style.display = "block";

  

  // Append user message

  chatBox.innerHTML += `<div style="margin-bottom: 12px; text-align: right;">

    <span style="display: inline-block; background: #2563eb; color: white; padding: 8px 12px; border-radius: 12px 12px 0 12px;">${msg}</span>

  </div>`;

  

  inputEl.value = "";

  

  // Append loading indicator

  const loadingId = "loading-" + Date.now();

  chatBox.innerHTML += `<div id="${loadingId}" style="margin-bottom: 12px; text-align: left;">
    <span style="display: inline-block; background: #e5e7eb; color: #111827; padding: 8px 12px; border-radius: 12px 12px 12px 0;">🤔 생각중...</span>
  </div>`;

  

  chatBox.scrollTop = chatBox.scrollHeight;

  

  try {

    const res = await fetch("/api/chat/", {

      method: "POST",

      headers: {

        "Content-Type": "application/json"

      },

      body: JSON.stringify({ message: msg })

    });

    

    const data = await res.json();

    const loadingEl = document.getElementById(loadingId);

    if (loadingEl) loadingEl.remove();

    

    if (data.reply) {

      const parsedHTML = typeof marked !== "undefined" ? marked.parse(data.reply) : data.reply;

      chatBox.innerHTML += `<div style="margin-bottom: 12px; text-align: left;">

        <div style="display: inline-block; background: white; border: 1px solid #d1d5db; color: #111827; padding: 12px; border-radius: 12px 12px 12px 0; width: 100%; box-sizing: border-box;">${parsedHTML}</div>

      </div>`;

    } else {

      chatBox.innerHTML += `<div style="margin-bottom: 12px; text-align: left;">

        <span style="display: inline-block; background: #fee2e2; color: #b91c1c; padding: 8px 12px; border-radius: 12px 12px 12px 0;">����: ${data.error || "�� �� ���� ������ �߻��߽��ϴ�."}</span>

      </div>`;

    }

  } catch (err) {

    const loadingEl = document.getElementById(loadingId);

    if (loadingEl) loadingEl.remove();

    chatBox.innerHTML += `<div style="margin-bottom: 12px; text-align: left;">

      <span style="display: inline-block; background: #fee2e2; color: #b91c1c; padding: 8px 12px; border-radius: 12px 12px 12px 0;">��Ʈ��ũ ������ �߻��߽��ϴ�.</span>

    </div>`;

  }

  

  chatBox.scrollTop = chatBox.scrollHeight;
}



