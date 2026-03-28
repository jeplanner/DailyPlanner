SUMMARY_TEMPLATE = """
<style>
  body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    background: #f6f7f9;
    margin: 0;
    padding: 16px;
  }

  .summary-title {
    font-size: 22px;
    font-weight: 700;
    margin: 12px 0 18px;
  }

  .section {
    margin-bottom: 18px;
  }

  .card {
    background: #ffffff;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 24px rgba(0,0,0,0.06);
  }

  /* ---------- TOGGLE ---------- */

  .planner-toggle{
    display:flex;
    gap:6px;
    margin-bottom:14px;
    background:#eef2f7;
    padding:4px;
    border-radius:10px;
    width:fit-content;
  }

  .toggle-btn{
    text-decoration:none;
    font-size:13px;
    font-weight:600;
    padding:6px 10px;
    border-radius:8px;
    color:#6b7280;
    transition:all 0.2s ease;
  }

  .toggle-btn.active{
    background:#ffffff;
    color:#2563eb;
    box-shadow:0 2px 6px rgba(0,0,0,0.08);
  }

  /* ---------- TABLE ---------- */

  .summary-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: auto;
  }

  .summary-table th {
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    color: #6b7280;
    padding: 10px 12px;
    background: #f9fafb;
  }

  .summary-table td {
    padding: 14px 12px;
    border-top: 1px solid #eef2f7;
    vertical-align: top;
    font-size: 15px;
    word-break: break-word;
    overflow-wrap: anywhere;
  }

  .summary-table td.time {
    font-weight: 700;
    color: #2563eb;
    white-space: nowrap;
  }

  .summary-table tr:hover {
    background: #f8fafc;
  }

  .empty {
    color: #9ca3af;
    font-style: italic;
    padding: 12px 0;
  }

  /* ---------- TEXT ---------- */

  .section h4 {
    margin: 0 0 8px;
    font-size: 15px;
    font-weight: 600;
  }

  .muted {
    color: #9ca3af;
  }

  /* ---------- STATS ---------- */

  .stats{
    display:flex;
    gap:12px;
    margin-bottom:18px;
  }

  .stat-card{
    flex:1;
    background:#ffffff;
    border-radius:16px;
    padding:16px;
    text-align:center;
    box-shadow:0 10px 24px rgba(0,0,0,0.06);
  }

  .stat-value{
    font-size:26px;
    font-weight:800;
    color:#2563eb;
  }

  .stat-label{
    font-size:13px;
    color:#6b7280;
    margin-top:4px;
  }

  .streak{
    display:flex;
    gap:8px;
  }

  .streak .day{
    width:24px;
    height:24px;
    border-radius:6px;
    background:#e5e7eb;
  }

  .streak .day.on{
    background:#22c55e;
  }

  /* ---------- MOBILE ---------- */

  @media (max-width: 600px){

    body{
      padding:10px;
    }

    .summary-title{
      font-size:18px;
    }

    .card{
      padding:12px;
    }

    .planner-toggle{
      width:100%;
    }

    .toggle-btn{
      flex:1;
      text-align:center;
    }

    .summary-table,
    .summary-table thead,
    .summary-table tbody,
    .summary-table tr,
    .summary-table td {
      display: block;
      width: 100%;
    }

    .summary-table thead {
      display: none;
    }

    .summary-table tr {
      margin-bottom: 12px;
      padding: 10px;
      border-radius: 12px;
      background: #ffffff;
      box-shadow: 0 4px 10px rgba(0,0,0,0.04);
    }

    .summary-table td {
      border: none;
      padding: 6px 0;
      font-size: 14px;
    }

    .summary-table td.time {
      width: auto;
      font-size: 13px;
      margin-bottom: 4px;
    }

    .stats{
      flex-direction:column;
    }
  }

</style>

<div class="nav-icons">
  {% include "_top_nav.html" %}
</div>

<!-- ================= TOGGLE ================= -->

<div class="planner-toggle">

  <a href="?view={{ view }}{% if view == 'weekly' %}&week={{ selected_week }}{% else %}&date={{ date }}{% endif %}&mode=slots"
     class="toggle-btn {{ 'active' if request.args.get('mode', 'slots') == 'slots' else '' }}">
    Slot Planner
  </a>

  <a href="?view={{ view }}{% if view == 'weekly' %}&week={{ selected_week }}{% else %}&date={{ date }}{% endif %}&mode=v2"
     class="toggle-btn {{ 'active' if request.args.get('mode') == 'v2' else '' }}">
    Planner V2
  </a>

</div>

<!-- ================= DAILY ================= -->

{% if view == "daily" %}

<h2 class="summary-title">
  📊 Daily Summary – {{ date.strftime("%d %b %Y") if date else "" }}
</h2>

<div class="section card">
  <table class="summary-table">
    <thead>
      <tr>
        <th>Time</th>
        <th>Task</th>
      </tr>
    </thead>
    <tbody>
      {% for t in data.tasks %}
        <tr>
          <td class="time">{{ t.time_label }}</td>
          <td>{{ t.text }}</td>
        </tr>
      {% else %}
        <tr>
          <td colspan="2" class="empty">No tasks scheduled</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="section card">
  <h4>🔥 Habits</h4>
  {% if data.habits %}
    {{ data.habits | join(", ") }}
  {% else %}
    <div class="muted">—</div>
  {% endif %}
</div>

<div class="section card">
  <h4>✍️ Reflection</h4>
  {% if data.reflection %}
    {{ data.reflection }}
  {% else %}
    <div class="muted">—</div>
  {% endif %}
</div>

<!-- ================= WEEKLY ================= -->

{% else %}

<form method="get" style="margin-bottom:16px;">
  <input type="hidden" name="view" value="weekly">
  <input type="hidden" name="mode" value="{{ request.args.get('mode','slots') }}">

  <label style="font-size:14px;font-weight:600;">📆 Select Week</label><br>

  <input type="week"
         name="week"
         value="{{ selected_week }}"
         onchange="this.form.submit()"
         style="margin-top:6px;padding:8px;border-radius:10px;border:1px solid #e5e7eb;">
</form>

<h2 class="summary-title">
  📆 Weekly Review
  <span class="muted">
    {{ start.strftime("%d %b") }} – {{ end.strftime("%d %b %Y") }}
  </span>
</h2>

<div class="stats">
  <div class="stat-card">
    <div class="stat-value">{{ data.focused_hours }}</div>
    <div class="stat-label">Focus Hours</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ data.habit_days }}/7</div>
    <div class="stat-label">Habit Days</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{{ data.completion_rate }}%</div>
    <div class="stat-label">Completion</div>
  </div>
</div>

<div class="section card">
  <h4>🧠 Weekly Insights</h4>
  <ul>
    {% for i in insights %}
      <li>{{ i }}</li>
    {% endfor %}
  </ul>

  <h4>🔥 Habit Streak</h4>
  <div class="streak">
    {% for i in range(7) %}
      <div class="day {{ 'on' if i < data.habit_days else '' }}"></div>
    {% endfor %}
  </div>
</div>

<div class="section card">
  <h4>✍️ Reflection Highlights</h4>

  {% if data.reflections %}
    <ul>
      {% for r in data.reflections %}
        <li>{{ r }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <div class="muted">No reflections logged</div>
  {% endif %}
</div>

{% for day, tasks in data.days.items() %}
  <div class="section card">
    <h4>{{ day }}</h4>

    <table class="summary-table">
      <tbody>
        {% for t in tasks %}
          <tr>
            <td class="time">{{ t.label }}</td>
            <td>{{ t.text }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
{% endfor %}

{% endif %}
"""