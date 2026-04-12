import re

path = r'c:\Users\Minjun\Downloads\minjeon_project\minjeon\templates\offices\result.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

new_ui = '''    <!-- 소요시간 타임라인 바 -->
    <div class="score-bars" style="margin-top: 15px;">
      <div class="score-row">
        <span class="score-label">🚗 카카오내비 이동</span>
        <div class="score-bar-wrap">
          <!-- Max 60min as 100% just for visualization scaling, capping at 100% -->
          <div class="score-bar score-bar--blue" style="width: {% widthratio office.times.driving 60 100 %}%"></div>
        </div>
        <span class="score-num">{{ office.times.driving }}분</span>
      </div>
      <div class="score-row">
        <span class="score-label">👥 예상 대기현황</span>
        <div class="score-bar-wrap">
          {% if office.waiting_count == -1 %}
          <div class="score-bar" style="width: 100%; background: #e5e7eb; color: #6b7280; font-size: 0.8rem; display: flex; align-items: center; justify-content: center;">준비 중</div>
          {% else %}
          <div class="score-bar score-bar--purple" style="width: {% widthratio office.times.waiting 60 100 %}%"></div>
          {% endif %}
        </div>
        <span class="score-num">{% if office.waiting_count == -1 %}-{% else %}{{ office.times.waiting }}분{% endif %}</span>
      </div>
    </div>'''

pattern = re.compile(r'    <!-- 소요시간 타임라인 바 -->.*?</div>\s*</div>\s*</div>', re.DOTALL)
new_text = pattern.sub(new_ui, text)

# Also update the value for wait count
wait_ui = '''      <div class="metric">
        <div class="metric-value {% if office.waiting_count == -1 %}gray{% elif office.waiting_count == 0 %}green{% elif office.waiting_count <= 7 %}yellow{% else %}red{% endif %}">
          {% if office.waiting_count == -1 %}❌{% else %}{{ office.waiting_count }}명{% endif %}
        </div>
        <div class="metric-label">현재 대기</div>
      </div>'''
      
text2 = re.sub(r'      <div class="metric">\s*<div class="metric-value.*?</div>\s*<div class="metric-label">현재 대기</div>\s*</div>', wait_ui, new_text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text2)

print("Updated result.html")
