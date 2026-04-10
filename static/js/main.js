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
          if (data.supported) {
            textEl.textContent = `위치 감지 완료 (가능한 지역: ${data.region})`;
            statusEl.querySelector('.dot').className = 'dot dot-green';
          } else {
            textEl.innerHTML = `위치 감지 완료 (<span style="color: #ef4444;">현재 불가능한 지역</span>)`;
            statusEl.querySelector('.dot').className = 'dot dot-red';
            
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
