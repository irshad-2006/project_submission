import calendar
from datetime import datetime, date, time as dtime

import streamlit as st

from utils import load_json, save_json, new_id, now_iso

FILE = "events.json"
CATEGORIES = ["Academic", "Cultural", "Technical", "Sports", "Club", "Other"]
CATEGORY_COLORS = {
    "Academic": "#F2C94C", "Cultural": "#EB5E8D", "Technical": "#F2994A",
    "Sports": "#4FD1C5", "Club": "#9B8AFB", "Other": "#C9C2AE",
}
CATEGORY_INK = {
    "Academic": "#6B540E", "Cultural": "#ffffff", "Technical": "#ffffff",
    "Sports": "#0E5F58", "Club": "#ffffff", "Other": "#4A4536",
}

st.set_page_config(page_title="Campus Marquee", page_icon="🎪", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
    .stApp{ background:#1B1F3B; color:#FBF8F1; }
    .marquee-title{ font-family:'Archivo Black', sans-serif; font-size:2.1rem; color:#FBF8F1; margin-bottom:0; }
    .marquee-sub{ font-family:'IBM Plex Mono', monospace; font-size:0.72rem; letter-spacing:1.6px;
        text-transform:uppercase; color:#F2C94C; margin-top:-4px; margin-bottom:18px; }
    .ticket{ display:flex; background:#FBF8F1; border-radius:10px; overflow:hidden; margin-bottom:12px;
        box-shadow:0 8px 20px rgba(0,0,0,0.25); }
    .ticket-date{ flex:0 0 74px; display:flex; flex-direction:column; align-items:center; justify-content:center;
        font-family:'Archivo Black', sans-serif; }
    .ticket-date .mon{ font-size:0.6rem; letter-spacing:1px; text-transform:uppercase; opacity:0.9; }
    .ticket-date .day{ font-size:1.6rem; line-height:1; }
    .ticket-date .wd{ font-family:'IBM Plex Mono', monospace; font-size:0.55rem; text-transform:uppercase; margin-top:2px; opacity:0.85; }
    .ticket-body{ flex:1; padding:12px 14px; color:#1B1F3B; }
    .ticket-title{ font-family:'Archivo Black', sans-serif; font-size:0.98rem; margin:0; }
    .ticket-meta{ font-family:'IBM Plex Mono', monospace; font-size:0.68rem; color:#5A5E82; margin-top:3px; }
    .ticket-desc{ font-size:0.82rem; color:#3d4160; margin:6px 0 0; }
    .ticket-cat{ font-family:'IBM Plex Mono', monospace; font-size:0.56rem; letter-spacing:0.6px; text-transform:uppercase;
        padding:2px 8px; border-radius:100px; float:right; }
    .cal-day-btn button{ width:100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="marquee-title">Campus Marquee</div>', unsafe_allow_html=True)
st.markdown('<div class="marquee-sub">College event calendar</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- state
if "events" not in st.session_state:
    st.session_state.events = load_json(FILE, [])
if "cal_year" not in st.session_state:
    st.session_state.cal_year = date.today().year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = date.today().month
if "selected_day" not in st.session_state:
    st.session_state.selected_day = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


def persist():
    save_json(FILE, st.session_state.events)


def fmt_time(t):
    if not t:
        return ""
    h, m = map(int, t.split(":"))
    ampm = "PM" if h >= 12 else "AM"
    h12 = ((h + 11) % 12) + 1
    return f"{h12}:{m:02d} {ampm}"


# ---------------------------------------------------------------- role + filters
role_col1, role_col2 = st.columns([3, 1])
with role_col2:
    st.session_state.is_admin = st.toggle("Admin view", value=st.session_state.is_admin)

search = st.text_input("Search events…", "")
cat_filter = st.multiselect("Filter by category", CATEGORIES, default=[])
show_favorites_only = st.checkbox("★ Favorites only", value=False)

# ---------------------------------------------------------------- calendar
st.markdown("#### Calendar")
nav1, nav2, nav3 = st.columns([1, 3, 1])
if nav1.button("‹ Prev"):
    st.session_state.cal_month -= 1
    if st.session_state.cal_month < 1:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
if nav3.button("Next ›"):
    st.session_state.cal_month += 1
    if st.session_state.cal_month > 12:
        st.session_state.cal_month = 1
        st.session_state.cal_year += 1
nav2.markdown(
    f"<div style='text-align:center;font-family:Archivo Black,sans-serif;padding-top:6px;'>"
    f"{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</div>",
    unsafe_allow_html=True,
)

events_by_day = {}
for ev in st.session_state.events:
    events_by_day.setdefault(ev["date"], []).append(ev["category"])

cal = calendar.Calendar(firstweekday=6)  # Sunday first
weeks = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
dow_cols = st.columns(7)
for i, d in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
    dow_cols[i].markdown(f"<div style='text-align:center;font-family:IBM Plex Mono,monospace;font-size:0.65rem;color:#5A5E82;'>{d}</div>", unsafe_allow_html=True)

today_iso = date.today().isoformat()
for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            iso = date(st.session_state.cal_year, st.session_state.cal_month, day).isoformat()
            dots = "".join(
                f'<span style="display:inline-block;width:5px;height:5px;border-radius:50%;'
                f'background:{CATEGORY_COLORS.get(c, "#C9C2AE")};margin:0 1px;"></span>'
                for c in events_by_day.get(iso, [])[:4]
            )
            label = f"**{day}**" if iso == today_iso else str(day)
            btn_type = "primary" if iso == st.session_state.selected_day else "secondary"
            if st.button(label, key=f"day_{iso}", use_container_width=True, type=btn_type):
                st.session_state.selected_day = None if st.session_state.selected_day == iso else iso
                st.rerun()
            if dots:
                st.markdown(f"<div style='text-align:center;'>{dots}</div>", unsafe_allow_html=True)

if st.session_state.selected_day and st.button("Clear day selection"):
    st.session_state.selected_day = None
    st.rerun()

# ---------------------------------------------------------------- add form
if st.session_state.is_admin:
    with st.expander("➕ Add event", expanded=False):
        with st.form("add_event", clear_on_submit=True):
            col1, col2 = st.columns(2)
            title = col1.text_input("Event title")
            organizer = col2.text_input("Organizer")
            description = st.text_area("Description", height=70)
            col3, col4, col5 = st.columns(3)
            ev_date = col3.date_input("Date", value=date.today())
            start_time = col4.time_input("Start time", value=dtime(10, 0))
            end_time = col5.time_input("End time", value=dtime(12, 0))
            location = st.text_input("Location")
            category = st.selectbox("Category", CATEGORIES)
            reminder = st.selectbox("Reminder", ["none", "1d", "3h", "1h"], index=1,
                                     format_func=lambda x: {"none": "No reminder", "1d": "1 day before",
                                                             "3h": "3 hours before", "1h": "1 hour before"}[x])
            submitted = st.form_submit_button("Save event")
            if submitted:
                if not title.strip():
                    st.error("Please enter a title.")
                else:
                    ev = {
                        "id": new_id("e"),
                        "title": title.strip(),
                        "organizer": organizer.strip(),
                        "description": description.strip(),
                        "date": ev_date.isoformat(),
                        "start_time": start_time.strftime("%H:%M"),
                        "end_time": end_time.strftime("%H:%M"),
                        "location": location.strip(),
                        "category": category,
                        "reminder": reminder,
                        "favorite": False,
                        "created_at": now_iso(),
                    }
                    st.session_state.events.append(ev)
                    persist()
                    st.session_state.cal_year = ev_date.year
                    st.session_state.cal_month = ev_date.month
                    st.success(f'Added "{title}".')
                    st.rerun()

# ---------------------------------------------------------------- list
st.markdown("#### " + (f"Events on {st.session_state.selected_day}" if st.session_state.selected_day else "Upcoming events"))

items = list(st.session_state.events)
if st.session_state.selected_day:
    items = [e for e in items if e["date"] == st.session_state.selected_day]
else:
    items = [e for e in items if e["date"] >= today_iso]
if cat_filter:
    items = [e for e in items if e["category"] in cat_filter]
if show_favorites_only:
    items = [e for e in items if e.get("favorite")]
if search:
    s = search.lower()
    items = [e for e in items if s in (e["title"] + e["description"] + e["location"] + e["organizer"]).lower()]
items.sort(key=lambda e: (e["date"], e["start_time"]))

if not items:
    st.markdown(
        '<div style="text-align:center;padding:40px;color:#5A5E82;'
        'font-family:\'IBM Plex Mono\',monospace;font-size:0.85rem;'
        'border:1px dashed #3A3F66;border-radius:10px;">No events match here.</div>',
        unsafe_allow_html=True,
    )

for ev in items:
    d = datetime.strptime(ev["date"], "%Y-%m-%d")
    color = CATEGORY_COLORS.get(ev["category"], "#C9C2AE")
    ink = CATEGORY_INK.get(ev["category"], "#4A4536")
    st.markdown(
        f"""
        <div class="ticket">
            <div class="ticket-date" style="background:{color};color:{ink};">
                <div class="mon">{d.strftime('%b')}</div>
                <div class="day">{d.day}</div>
                <div class="wd">{d.strftime('%a')}</div>
            </div>
            <div class="ticket-body">
                <span class="ticket-cat" style="background:{color};color:{ink};">{ev['category']}</span>
                <p class="ticket-title">{'★ ' if ev.get('favorite') else ''}{ev['title']}</p>
                <div class="ticket-meta">{fmt_time(ev['start_time'])} – {fmt_time(ev['end_time'])} · {ev['location'] or 'TBA'}</div>
                {f'<p class="ticket-desc">{ev["description"]}</p>' if ev['description'] else ''}
                <div class="ticket-meta">{f"Organized by {ev['organizer']} · " if ev['organizer'] else ''}
                    {"No reminder set" if ev['reminder']=="none" else "Reminder " + ev['reminder'] + " before"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    bc1, bc2 = st.columns([1, 1])
    fav_label = "☆ Unfavorite" if ev.get("favorite") else "☆ Favorite"
    if bc1.button(fav_label, key=f"fav_{ev['id']}"):
        ev["favorite"] = not ev.get("favorite", False)
        persist()
        st.rerun()
    if st.session_state.is_admin:
        if bc2.button("Delete", key=f"del_{ev['id']}"):
            st.session_state.events = [x for x in st.session_state.events if x["id"] != ev["id"]]
            persist()
            st.rerun()
    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

st.caption("Data is saved to `data/events.json` and persists across sessions.")
