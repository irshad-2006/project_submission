from datetime import datetime, date, time as dtime

import streamlit as st

from utils import load_json, save_json, new_id, now_iso

FILE = "assignments.json"
REMINDER_THRESHOLDS = [
    ("7d", 7 * 24 * 60 * 60),
    ("3d", 3 * 24 * 60 * 60),
    ("1d", 1 * 24 * 60 * 60),
    ("1h", 60 * 60),
]

st.set_page_config(page_title="Deadline Ledger", page_icon="📋", layout="centered")

# ---------------------------------------------------------------- styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
    .stApp{ background:#E8E4D9; }
    .ledger-title{ font-family:'Zilla Slab', serif; font-weight:700; font-size:2.1rem; color:#24303D; margin-bottom:0; }
    .ledger-sub{ font-family:'IBM Plex Mono', monospace; font-size:0.72rem; letter-spacing:1.5px;
        text-transform:uppercase; color:#5B6B79; margin-top:-6px; margin-bottom:18px; }
    .card{
        background:#F2EFE6; border:1px solid #A99F86; padding:16px 18px; border-radius:2px; margin-bottom:12px;
        display:flex; gap:16px; align-items:flex-start;
    }
    .stamp{
        flex:0 0 auto; width:58px; height:58px; border-radius:50%; border:2px solid currentColor;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        font-family:'IBM Plex Mono', monospace; transform: rotate(-8deg); text-align:center; line-height:1.1;
    }
    .stamp .num{ font-size:1.05rem; font-weight:600; }
    .stamp .unit{ font-size:0.48rem; letter-spacing:0.5px; text-transform:uppercase; margin-top:2px; }
    .stamp.high{ color:#B3401F; } .stamp.medium{ color:#B5811F; } .stamp.low{ color:#4C7A5D; } .stamp.done{ color:#5C6B62; }
    .card-title{ font-family:'Zilla Slab', serif; font-weight:600; font-size:1.1rem; color:#24303D; margin:0; }
    .card-subject{ font-family:'IBM Plex Mono', monospace; font-size:0.64rem; letter-spacing:1px; text-transform:uppercase; color:#5B6B79; }
    .card-desc{ font-size:0.85rem; color:#5B6B79; margin:6px 0 0; }
    .card-meta{ font-family:'IBM Plex Mono', monospace; font-size:0.7rem; color:#5B6B79; margin-top:8px; }
    .tag{ font-family:'IBM Plex Mono', monospace; font-size:0.58rem; letter-spacing:0.8px; text-transform:uppercase;
        padding:3px 8px; border-radius:2px; margin-left:6px; }
    .tag.High{ background:#F1DCD2; color:#B3401F; } .tag.Medium{ background:#F1E6CE; color:#B5811F; }
    .tag.Low{ background:#DCE7DF; color:#4C7A5D; } .tag.status{ background:#DEE3DE; color:#24303D; }
    .rem-chip{ font-family:'IBM Plex Mono', monospace; font-size:0.58rem; padding:2px 7px; border:1px solid #A99F86;
        color:#5B6B79; margin-right:4px; display:inline-block; margin-top:6px; }
    .rem-chip.fired{ background:#24303D; color:#fff; border-color:#24303D; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="ledger-title">Deadline Ledger</div>', unsafe_allow_html=True)
st.markdown('<div class="ledger-sub">Assignment tracking &amp; reminders</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- state
if "assignments" not in st.session_state:
    st.session_state.assignments = load_json(FILE, [])


def persist():
    save_json(FILE, st.session_state.assignments)


def due_dt(a):
    return datetime.strptime(a["due_date"] + "T" + a.get("due_time", "23:59"), "%Y-%m-%dT%H:%M")


def classify(a):
    if a["status"] == "Completed":
        return "completed"
    now = datetime.now()
    due = due_dt(a)
    if due < now:
        return "overdue"
    if due.date() == now.date():
        return "today"
    return "upcoming"


def stamp_info(a):
    if a["status"] == "Completed":
        return "✓", "done", "done"
    diff = (due_dt(a) - datetime.now()).total_seconds()
    late = diff < 0
    absd = abs(diff)
    if absd < 3600:
        num, unit = max(1, round(absd / 60)), "min"
    elif absd < 172800:
        num, unit = round(absd / 3600), "hr"
    else:
        num, unit = round(absd / 86400), "day"
    cls = "high" if late else ("high" if a["priority"] == "High" else "medium" if a["priority"] == "Medium" else "low")
    return ("−" if late else "") + str(num), unit + (" late" if late else " left"), cls


def next_status(status):
    return {"Pending": "In Progress", "In Progress": "Completed", "Overdue": "In Progress"}.get(status, "Pending")


# ---------------------------------------------------------------- stats
counts = {"today": 0, "upcoming": 0, "overdue": 0, "completed": 0}
for a in st.session_state.assignments:
    counts[classify(a)] += 1
c1, c2, c3, c4 = st.columns(4)
c1.metric("Today", counts["today"])
c2.metric("Upcoming", counts["upcoming"])
c3.metric("Overdue", counts["overdue"])
c4.metric("Completed", counts["completed"])

# ---------------------------------------------------------------- add form
with st.expander("➕ Add assignment", expanded=False):
    with st.form("add_assignment", clear_on_submit=True):
        col1, col2 = st.columns(2)
        title = col1.text_input("Assignment title")
        subject = col2.text_input("Subject")
        description = st.text_area("Description", height=70)
        col3, col4 = st.columns(2)
        due_date = col3.date_input("Due date", value=date.today())
        due_time = col4.time_input("Due time", value=dtime(23, 59))
        attachment = st.text_input("Attachment (optional link or filename)")
        priority = st.radio("Priority", ["Low", "Medium", "High"], index=1, horizontal=True)
        submitted = st.form_submit_button("Save assignment")
        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
            else:
                a = {
                    "id": new_id("a"),
                    "title": title.strip(),
                    "subject": subject.strip(),
                    "description": description.strip(),
                    "due_date": due_date.isoformat(),
                    "due_time": due_time.strftime("%H:%M"),
                    "priority": priority,
                    "status": "Pending",
                    "attachment": attachment.strip(),
                    "created_at": now_iso(),
                    "completed_at": None,
                }
                st.session_state.assignments.append(a)
                persist()
                st.success(f'Added "{title}".')
                st.rerun()

# ---------------------------------------------------------------- tabs
tab_defs = [("today", "Today"), ("upcoming", "Upcoming"), ("overdue", "Overdue"),
            ("completed", "Completed"), ("all", "All")]
tabs = st.tabs([f"{label} ({counts.get(key, len(st.session_state.assignments)) if key != 'all' else len(st.session_state.assignments)})"
                for key, label in tab_defs])

for (key, label), tab in zip(tab_defs, tabs):
    with tab:
        items = [a for a in st.session_state.assignments if key == "all" or classify(a) == key]
        items.sort(key=due_dt)
        if not items:
            st.markdown(
                '<div style="text-align:center;padding:40px;color:#5B6B79;'
                'font-family:\'IBM Plex Mono\',monospace;font-size:0.85rem;'
                'border:1px dashed #A99F86;">Nothing here.</div>',
                unsafe_allow_html=True,
            )
        for a in items:
            num, unit, cls = stamp_info(a)
            reminders = []
            remaining = (due_dt(a) - datetime.now()).total_seconds()
            for lbl, secs in REMINDER_THRESHOLDS:
                fired = remaining <= secs and a["status"] != "Completed"
                reminders.append(f'<span class="rem-chip {"fired" if fired else ""}">{lbl} {"sent" if fired else "pending"}</span>')

            status_label = "Overdue" if classify(a) == "overdue" and a["status"] != "Completed" else a["status"]

            st.markdown(
                f"""
                <div class="card">
                    <div class="stamp {cls}"><div class="num">{num}</div><div class="unit">{unit}</div></div>
                    <div style="flex:1;">
                        <p class="card-title">{a['title']}
                            <span class="tag {a['priority']}">{a['priority']}</span>
                            <span class="tag status">{status_label}</span>
                        </p>
                        <div class="card-subject">{a['subject'] or 'General'}</div>
                        {f'<p class="card-desc">{a["description"]}</p>' if a['description'] else ''}
                        <div class="card-meta">Due {a['due_date']} · {a['due_time']}
                            {f" · 📎 {a['attachment']}" if a['attachment'] else ''}</div>
                        <div>{''.join(reminders)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            bcol1, bcol2, bcol3 = st.columns([1, 1, 1])
            if a["status"] != "Completed":
                if bcol1.button(f"Mark as {next_status(a['status'])}", key=f"adv_{a['id']}_{key}"):
                    a["status"] = next_status(a["status"])
                    if a["status"] == "Completed":
                        a["completed_at"] = now_iso()
                    persist()
                    st.rerun()
                if bcol2.button("Mark completed", key=f"comp_{a['id']}_{key}"):
                    a["status"] = "Completed"
                    a["completed_at"] = now_iso()
                    persist()
                    st.rerun()
            else:
                if bcol1.button("Reopen", key=f"reopen_{a['id']}_{key}"):
                    a["status"] = "Pending"
                    a["completed_at"] = None
                    persist()
                    st.rerun()
            if bcol3.button("Delete", key=f"del_{a['id']}_{key}"):
                st.session_state.assignments = [x for x in st.session_state.assignments if x["id"] != a["id"]]
                persist()
                st.rerun()
            st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

st.caption("Data is saved to `data/assignments.json` and persists across sessions.")
