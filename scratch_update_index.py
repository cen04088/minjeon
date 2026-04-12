import re

path = r'c:\Users\Minjun\Downloads\minjeon_project\minjeon\templates\offices\index.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

new_ui = '''    <!-- 검색 모드 선택 -->
    <div class="form-group" style="margin-bottom: 20px;">
      <label class="form-label">탐색 방식</label>
      <div style="display: flex; gap: 10px;">
        <label class="mode-chip" style="flex: 1; text-align: center; padding: 12px;">
          <input type="radio" name="search_mode" value="GENERAL" checked>
          <span style="display: block;">🌐 일반 모드<br><small style="font-weight: normal;">(전국 지원지 탐색)</small></span>
        </label>
        <label class="mode-chip" style="flex: 1; text-align: center; padding: 12px;">
          <input type="radio" name="search_mode" value="PREDICTION">
          <span style="display: block;">⏱️ 예측 모드<br><small style="font-weight: normal;">(41곳 실시간 반영)</small></span>
        </label>
      </div>
    </div>

    <!-- 민원 업무 선택 -->
    <div class="form-group">
      <label class="form-label">처리할 민원 업무</label>
      {% for category, tasks in service_choices.items %}
      <div class="category-block" style="margin-bottom: 15px;">
        <div style="font-size: 0.9rem; color: #4b5563; font-weight: 600; margin-bottom: 8px;">🔹 {{ category }}</div>
        <div class="service-grid">
          {% for svc in tasks %}
          <label class="service-chip">
            <input type="radio" name="service" value="{{ svc }}" {% if forloop.parentloop.first and forloop.first %}checked{% endif %}>
            <span>{{ svc }}</span>
          </label>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </div>'''

pattern = re.compile(r'    <!-- 민원 업무 선택 -->.*?</div>\s*</div>', re.DOTALL)
new_text = pattern.sub(new_ui, text)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Updated index.html")
