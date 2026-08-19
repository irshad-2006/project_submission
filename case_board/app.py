import re
from datetime import datetime, date, time as dtime

import streamlit as st

from utils import load_json, save_json, new_id, now_iso

FILE = "case_board.json"
META_FILE = "case_board_meta.json"
CATEGORIES = ["Earphones", "Wallet", "Bag", "Phone", "Keys", "ID Card", "Bottle", "Umbrella", "Laptop", "Other"]
THRESHOLD = 50

st.set_page_config(page_title="Case Board", page_icon="🕵️", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
    .stApp{ background:#3B2E22; color:#E8D9B0; }
    .case-title{ font-family:'Special Elite', cursive; font-size:2rem; color:#F7F2E4; text-align:center; margin-bottom:0; }
    .case-sub{ font-family:'IBM Plex Mono', monospace; font-size:0.7rem; letter-spacing:2px; text-transform:uppercase;
        color:#B3872F; text-align:center; margin-top:4px; margin-bottom:18px; }
    .rcard{ background:#E8D9B0; border-radius:3px; padding:14px 16px; margin-bottom:10px; color:#2B2118; }
    .rtag{ font-family:'IBM Plex Mono', monospace; font-size:0.58rem; letter-spacing:1px; text-transform:uppercase;
        padding:2px 8px; border-radius:100px; font-weight:600; }
    .rtag.LOST{ background:#DDE8F2; color:#3B6EA5; } .rtag.FOUND{ background:#E1EEDD; color:#4C8C4A; }
    .rtitle{ font-family:'Special Elite', cursive; font-size:1rem; margin:6px 0 2px; }
    .rmeta{ font-family:'IBM Plex Mono', monospace; font-size:0.68rem; color:#6B5A45; }
    .rdesc{ font-size:0.82rem; margin-top:6px; color:#3d3223; }
    .match{ background:#E8D9B0; border-radius:4px; padding:16px 18px; margin-bottom:14px; color:#2B2118; }
    .stamp-badge{ width:60px; height:60px; border-radius:50%; border:3px solid #A5342E; color:#A5342E;
        display:flex; flex-direction:column; align-items:center; justify-content:center; font-family:'IBM Plex Mono', monospace;
        margin:0 auto; }
    .stamp-badge.high{ border-color:#4C8C4A; color:#4C8C4A; }
    .stamp-badge .pct{ font-size:0.95rem; font-weight:700; line-height:1; }
    .stamp-badge .lbl{ font-size:0.4rem; letter-spacing:0.5px; text-transform:uppercase; margin-top:2px; }
    .verdict{ text-align:center; font-family:'IBM Plex Mono', monospace; font-size:0.58rem; text-transform:uppercase;
        color:#6B5A45; margin-top:4px; }
    .notif-item{ font-family:'IBM Plex Mono', monospace; font-size:0.72rem; color:#E8D9B0; opacity:0.85; padding:4px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="case-title">The Case Board</div>', unsafe_allow_html=True)
st.markdown('<div class="case-sub">Smart matching · campus lost &amp; found</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- state
if "reports" not in st.session_state:
    st.session_state.reports = load_json(FILE, [])
if "meta" not in st.session_state:
    st.session_state.meta = load_json(META_FILE, {"notified": [], "dismissed": [], "notifications": []})


def persist_reports():
    save_json(FILE, st.session_state.reports)


def persist_meta():
    save_json(META_FILE, st.session_state.meta)


def pair_key(a, b):
    return "|".join(sorted([a, b]))


def to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


def text_similarity(a, b):
    if not a or not b:
        return 0.0
    wa = {w for w in re.split(r"\W+", a.lower()) if len(w) > 2}
    wb = {w for w in re.split(r"\W+", b.lower()) if len(w) > 2}
    if not wa or not wb:
        return 0.0
    overlap = len(wa & wb)
    return overlap / max(len(wa), len(wb))


def compute_score(lost, found):
    dims = [
        (15, 1 if lost["category"] and found["category"] and lost["category"] == found["category"] else 0),
        (8, 1 if lost["color"] and found["color"] and lost["color"].strip().lower() == found["color"].strip().lower() else 0),
        (15, 1 if lost["brand"] and found["brand"] and lost["brand"].strip().lower() == found["brand"].strip().lower() else 0),
        (15, 1 if lost["location"] and found["location"] and lost["location"].strip().lower() == found["location"].strip().lower() else 0),
        (15, 1 if lost["date"] and found["date"] and lost["date"] == found["date"] else 0),
        (7, max(0, 1 - abs(to_minutes(lost["time"]) - to_minutes(found["time"])) / 180) if lost["time"] and found["time"] else 0),
        (10, text_similarity(lost["description"], found["description"])),
        (15, 1 if lost["has_photo"] and found["has_photo"] else 0),
    ]
    total_w = sum(w for w, _ in dims)
    gained = sum(w * m for w, m in dims)
    return round((gained / total_w) * 100)


def all_matches():
    lost = [r for r in st.session_state.reports if r["type"] == "LOST" and not r["resolved"]]
    found = [r for r in st.session_state.reports if r["type"] == "FOUND" and not r["resolved"]]
    dismissed = set(st.session_state.meta.get("dismissed", []))
    out = []
    for l in lost:
        for f in found:
            key = pair_key(l["id"], f["id"])
            if key in dismissed:
                continue
            score = compute_score(l, f)
            if score >= THRESHOLD:
                out.append({"lost": l, "found": f, "score": score})
    out.sort(key=lambda m: -m["score"])
    return out


def refresh_notifications(matches):
    notified = set(st.session_state.meta.get("notified", []))
    changed = False
    for m in matches:
        key = pair_key(m["lost"]["id"], m["found"]["id"])
        if key not in notified:
            notified.add(key)
            st.session_state.meta.setdefault("notifications", []).insert(0, {
                "text": f"Possible match — \"{m['lost']['itemName']}\" (lost) ↔ \"{m['found']['itemName']}\" (found) — {m['score']}% similarity",
                "time": now_iso(),
            })
            changed = True
    if changed:
        st.session_state.meta["notified"] = list(notified)
        persist_meta()


matches = all_matches()
refresh_notifications(matches)

# ---------------------------------------------------------------- stats
lost_open = len([r for r in st.session_state.reports if r["type"] == "LOST" and not r["resolved"]])
found_open = len([r for r in st.session_state.reports if r["type"] == "FOUND" and not r["resolved"]])
resolved_ct = len([r for r in st.session_state.reports if r["resolved"]])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Lost open", lost_open)
c2.metric("Found open", found_open)
c3.metric("Possible matches", len(matches))
c4.metric("Resolved", resolved_ct)

with st.expander("🔔 Notification log", expanded=False):
    notifs = st.session_state.meta.get("notifications", [])
    if not notifs:
        st.caption("No possible matches identified yet.")
    for n in notifs[:8]:
        st.markdown(f'<div class="notif-item">{n["time"]} — {n["text"]}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- forms
fcol1, fcol2 = st.columns(2)
with fcol1:
    with st.expander("✎ Report a lost item"):
        with st.form("lost_form", clear_on_submit=True):
            name = st.text_input("Item name", key="l_name")
            category = st.selectbox("Category", CATEGORIES, key="l_cat")
            colc1, colc2 = st.columns(2)
            color = colc1.text_input("Color", key="l_color")
            brand = colc2.text_input("Brand", key="l_brand")
            location = st.text_input("Location", key="l_loc")
            dtc1, dtc2 = st.columns(2)
            ldate = dtc1.date_input("Date lost", value=date.today(), key="l_date")
            ltime = dtc2.time_input("Time", value=dtime(12, 0), key="l_time")
            reporter = st.text_input("Reported by (optional)", key="l_reporter")
            description = st.text_area("Description", key="l_desc", height=70)
            has_photo = st.checkbox("I have a photo of this item", key="l_photo")
            if st.form_submit_button("File lost report"):
                if not name.strip():
                    st.error("Please enter an item name.")
                else:
                    r = {
                        "id": new_id("r"), "type": "LOST", "itemName": name.strip(), "category": category,
                        "color": color.strip(), "brand": brand.strip(), "location": location.strip(),
                        "date": ldate.isoformat(), "time": ltime.strftime("%H:%M"), "reporter": reporter.strip(),
                        "description": description.strip(), "has_photo": has_photo, "resolved": False,
                        "created_at": now_iso(),
                    }
                    st.session_state.reports.insert(0, r)
                    persist_reports()
                    st.success(f'Filed lost report for "{name}".')
                    st.rerun()

with fcol2:
    with st.expander("✎ Report a found item"):
        with st.form("found_form", clear_on_submit=True):
            name = st.text_input("Item name", key="f_name")
            category = st.selectbox("Category", CATEGORIES, key="f_cat")
            colc1, colc2 = st.columns(2)
            color = colc1.text_input("Color", key="f_color")
            brand = colc2.text_input("Brand", key="f_brand")
            location = st.text_input("Location found", key="f_loc")
            dtc1, dtc2 = st.columns(2)
            fdate = dtc1.date_input("Date found", value=date.today(), key="f_date")
            ftime = dtc2.time_input("Time", value=dtime(12, 0), key="f_time")
            reporter = st.text_input("Reported by (optional)", key="f_reporter")
            description = st.text_area("Description", key="f_desc", height=70)
            has_photo = st.checkbox("I have a photo of this item", key="f_photo")
            if st.form_submit_button("File found report"):
                if not name.strip():
                    st.error("Please enter an item name.")
                else:
                    r = {
                        "id": new_id("r"), "type": "FOUND", "itemName": name.strip(), "category": category,
                        "color": color.strip(), "brand": brand.strip(), "location": location.strip(),
                        "date": fdate.isoformat(), "time": ftime.strftime("%H:%M"), "reporter": reporter.strip(),
                        "description": description.strip(), "has_photo": has_photo, "resolved": False,
                        "created_at": now_iso(),
                    }
                    st.session_state.reports.insert(0, r)
                    persist_reports()
                    st.success(f'Filed found report for "{name}".')
                    st.rerun()

# ---------------------------------------------------------------- tabs
tab_labels = [
    f"Possible matches ({len(matches)})",
    f"Lost reports ({lost_open})",
    f"Found reports ({found_open})",
    f"Resolved ({resolved_ct})",
]
t1, t2, t3, t4 = st.tabs(tab_labels)


def report_card(r):
    st.markdown(
        f"""
        <div class="rcard">
            <span class="rtag {r['type']}">{r['type']}</span>
            <div class="rtitle">{r['itemName']}</div>
            <div class="rmeta">{r['category']} · {r['color'] or '—'} · {r['brand'] or '—'}</div>
            <div class="rmeta">{r['location'] or 'Unknown location'} · {r['date']} {('· ' + r['time']) if r['time'] else ''}</div>
            {f'<div class="rdesc">{r["description"]}</div>' if r['description'] else ''}
            {'<div class="rmeta">📷 Photo on file</div>' if r['has_photo'] else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
    bc1, bc2 = st.columns(2)
    if not r["resolved"]:
        if bc1.button("Mark resolved", key=f"resolve_{r['id']}"):
            r["resolved"] = True
            persist_reports()
            st.rerun()
    else:
        if bc1.button("Reopen", key=f"reopen_{r['id']}"):
            r["resolved"] = False
            persist_reports()
            st.rerun()
    if bc2.button("Delete", key=f"delete_{r['id']}"):
        st.session_state.reports = [x for x in st.session_state.reports if x["id"] != r["id"]]
        persist_reports()
        st.rerun()


with t1:
    if not matches:
        st.markdown(
            '<div style="text-align:center;padding:40px;opacity:0.6;font-family:\'IBM Plex Mono\',monospace;'
            'border:1px dashed rgba(255,255,255,0.2);border-radius:6px;">No possible matches yet. '
            'File a lost and a found report with overlapping details to see the engine work.</div>',
            unsafe_allow_html=True,
        )
    for m in matches:
        high = m["score"] >= 80
        l, f = m["lost"], m["found"]
        mc1, mc2, mc3 = st.columns([2, 1, 2])
        with mc1:
            st.markdown(
                f'<span class="rtag LOST">LOST</span><div class="rtitle">{l["itemName"]}</div>'
                f'<div class="rmeta">{l["location"] or "—"} · {l["date"]}</div>'
                f'<div class="rmeta">{l["color"] or "—"} · {l["brand"] or "—"}</div>',
                unsafe_allow_html=True,
            )
        with mc2:
            st.markdown(
                f'<div class="stamp-badge {"high" if high else ""}"><div class="pct">{m["score"]}%</div>'
                f'<div class="lbl">match</div></div>'
                f'<div class="verdict">{"High confidence" if high else "Possible match"}</div>',
                unsafe_allow_html=True,
            )
        with mc3:
            st.markdown(
                f'<span class="rtag FOUND">FOUND</span><div class="rtitle">{f["itemName"]}</div>'
                f'<div class="rmeta">{f["location"] or "—"} · {f["date"]}</div>'
                f'<div class="rmeta">{f["color"] or "—"} · {f["brand"] or "—"}</div>',
                unsafe_allow_html=True,
            )
        ac1, ac2 = st.columns(2)
        if ac1.button("Confirm & resolve both", key=f"confirm_{l['id']}_{f['id']}"):
            l["resolved"] = True
            f["resolved"] = True
            persist_reports()
            st.rerun()
        if ac2.button("Not a match", key=f"dismiss_{l['id']}_{f['id']}"):
            st.session_state.meta.setdefault("dismissed", []).append(pair_key(l["id"], f["id"]))
            persist_meta()
            st.rerun()
        st.markdown("<hr style='opacity:0.15;'>", unsafe_allow_html=True)

with t2:
    lost_items = [r for r in st.session_state.reports if r["type"] == "LOST" and not r["resolved"]]
    if not lost_items:
        st.caption("No open lost reports.")
    for r in lost_items:
        report_card(r)

with t3:
    found_items = [r for r in st.session_state.reports if r["type"] == "FOUND" and not r["resolved"]]
    if not found_items:
        st.caption("No open found reports.")
    for r in found_items:
        report_card(r)

with t4:
    resolved_items = [r for r in st.session_state.reports if r["resolved"]]
    if not resolved_items:
        st.caption("Nothing resolved yet.")
    for r in resolved_items:
        report_card(r)

st.caption("Reports are saved to `data/case_board.json` and persist across sessions. "
           "Matching runs entirely on the details you enter — no real photos are analyzed in this demo.")
