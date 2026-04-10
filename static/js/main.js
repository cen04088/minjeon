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

      textEl.textContent = `위치 감지 완료 (${lat}, ${lng})`;
      statusEl.querySelector('.dot').className = 'dot dot-green';
      if (submitBtn) submitBtn.disabled = false;
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
