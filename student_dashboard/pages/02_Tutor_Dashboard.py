import streamlit as st
import pandas as pd
import datetime
from utils.db import supabase
from utils.chatbot import process_query 

st.set_page_config(page_title="Tutor Dashboard", layout="wide", page_icon="👨‍🏫")

if 'user' not in st.session_state or st.session_state['role'] != 'tutor':
    st.warning("⛔ Access Denied")
    st.stop()

def apply_theme():
    is_light = st.session_state.get('theme_light', False)
    bg_color = "#f8f9fa" if is_light else "#0e1117"
    text_color = "#212529" if is_light else "#fafafa"
    card_bg = "#ffffff" if is_light else "#1e2130"
    border_color = "#dee2e6" if is_light else "#444"
    input_bg = "#ffffff" if is_light else "#1e2130"
    chat_bot_bg = "#ffffff" if is_light else "#2d2f3d"

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown p {{ color: {text_color} !important; }}
        [data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
        [data-testid="stChatMessage"] {{ background-color: {chat_bot_bg}; border: 1px solid {border_color}; border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem; }}
        [data-testid="stMetric"] {{ background-color: {card_bg}; padding: 15px; border-radius: 8px; border: 1px solid {border_color}; text-align: center; }}
        .stMetricLabel {{ font-weight: bold; color: #888 !important; }}
        .stMetricValue {{ font-weight: 900; color: {text_color} !important; font-size: 1.8rem !important; }}
        .stTextInput input, .stNumberInput input, .stDateInput input, .stChatInput textarea {{ background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {border_color} !important; }}
        thead tr th {{ background-color: {card_bg} !important; color: {text_color} !important; border-bottom: 2px solid {border_color} !important; }}
        .profile-card {{ background-color: {card_bg}; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; border: 1px solid {border_color}; }}
    </style>
    """, unsafe_allow_html=True)

apply_theme()


def render_analytics(df_input):
    if df_input is None or (isinstance(df_input, pd.DataFrame) and df_input.empty): 
        return
    df = df_input.copy()

     
    if "Date" in df.columns and "Status" in df.columns:
        st.subheader("📅 Detailed History Log")
        def highlight_status(val):
            if val == 'Absent': return 'background-color: #fee2e2; color: #b91c1c; font-weight: bold'
            if val == 'OD': return 'background-color: #fef3c7; color: #92400e; font-weight: bold'
            return ''
        st.dataframe(df.style.applymap(highlight_status, subset=['Status']), use_container_width=True, hide_index=True)
        return 

    
    if "Marks" in df.columns:
        avg = df["Marks"].mean()
        
         
        failed_df = df[df["Marks"] < 50]
        least_perf_row = df.nsmallest(1, "Marks").iloc[0]

        col1, col2, col3 = st.columns(3)
        col1.metric("⭐ Class Average", f"{avg:.1f}")
        if "Attendance" in df.columns:
            col2.metric("📅 Attendance", f"{df['Attendance'].mean():.1f}%")
        
        top_subj = df.loc[df["Marks"].idxmax()]["Subject"]
        col3.metric("🏆 Top Subject", top_subj)
        
        st.markdown("---")
        
         
        a1, a2 = st.columns(2)
        with a1:
            if not failed_df.empty:
                st.error(f"❌ **Failed Subjects (<50):** {', '.join(failed_df['Subject'].tolist())}")
            else:
                st.success("✅ No Failed Subjects")
        
        with a2:
            st.warning(f"📉 **Least Performing:** {least_perf_row['Subject']} ({least_perf_row['Marks']} Marks)")
        
        st.markdown("---")
        
        # --- CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📊 Marks Performance")
            st.bar_chart(df.set_index("Subject")["Marks"], color="#10B981") 
        with c2:
            st.subheader("📉 Attendance Stats")
            if "Attendance" in df.columns: 
                st.bar_chart(df.set_index("Subject")["Attendance"], color="#3B82F6")

# ==========================================
# 🛠️ SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown(f"""
    <div class="profile-card">
        <p style="margin:0; font-size:0.85rem; color:#888 !important;">Logged In As</p>
        <p style="margin:0; font-size:1.2rem; font-weight:bold;">👨‍🏫 {st.session_state['user']['full_name']}</p>
        <hr style="margin: 10px 0; border-color: #eee;">
        <p style="margin:0; font-size:0.8rem; color:#888 !important;">Tutor Access • Panel V2.0</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("### ⚙️ Settings")
    light_mode = st.toggle("🌞 Light Mode", value=st.session_state.get('theme_light', False))
    if light_mode != st.session_state.get('theme_light', False):
        st.session_state['theme_light'] = light_mode
        st.rerun()
    st.divider()
    if st.button("🚪 Logout", type="primary", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")

# ==========================================
# 🛠️ DASHBOARD TABS
# ==========================================
st.title("👨‍🏫 Tutor Dashboard")
# Update this line to include tab4
tab1, tab2, tab3, tab4 = st.tabs(["📝 Enter Marks", "📅 Mark Attendance", "🤖 AI Student Assistant", "🚀 OD Approvals"])

with tab1:
    st.subheader("Update Subject Marks")
    try:
        students_data = supabase.table("users").select("*").eq("role", "student").execute().data
        subjects_data = supabase.table("subjects").select("*").execute().data
    except:
        students_data, subjects_data = [], []
    
    if students_data and subjects_data:
        c1, c2 = st.columns(2)
        with c1:
            s_name = st.selectbox("Select Student", [s['full_name'] for s in students_data], key="marks_s")
            sel_student = next(s for s in students_data if s['full_name'] == s_name)
        with c2:
            sub_name = st.selectbox("Select Subject", [s['name'] for s in subjects_data], key="marks_sub")
            sel_subject = next(s for s in subjects_data if s['name'] == sub_name)

        marks = st.number_input("Enter Marks (0-100)", 0, 100)
        
        if st.button("💾 Save Marks", use_container_width=True, type="primary"):
            try:
                existing = supabase.table("performance").select("*").eq("student_id", sel_student['id']).eq("subject_id", sel_subject['id']).execute().data
                data = {
                    "student_id": sel_student['id'], "subject_id": sel_subject['id'], "marks": marks,
                    "attendance": existing[0]['attendance'] if existing else 0,
                    "edit_count": (existing[0]['edit_count'] + 1) if existing else 0
                }
                if existing: supabase.table("performance").update(data).eq("id", existing[0]['id']).execute()
                else: supabase.table("performance").insert(data).execute()
                st.toast(f"✅ Marks Saved for {s_name}!")
            except Exception as e: st.error(f"Error: {e}")
    else:
        st.warning("Database empty. Please add students/subjects first.")

# ==========================================
# 📅 ATTENDANCE TAB (DYNAMIC ABSENT REASON)
# ==========================================
with tab2:
    st.subheader("📅 Subject-wise Daily Attendance")
    try:
        subjects_list = supabase.table("subjects").select("*").execute().data
        students_list = supabase.table("users").select("*").eq("role", "student").execute().data
    except:
        subjects_list, students_list = [], []

    if subjects_list and students_list:
        c1, c2 = st.columns(2)
        with c1:
            sel_subject_name = st.selectbox("Select Subject", [s['name'] for s in subjects_list], key="att_sub")
            subj_id_att = next(s['id'] for s in subjects_list if s['name'] == sel_subject_name)
        with c2:
            date_sel_att = st.date_input("Select Date", datetime.date.today(), key="att_date")

        existing_att_check = supabase.table("attendance_logs")\
            .select("*")\
            .eq("date", str(date_sel_att))\
            .eq("subject_id", subj_id_att).execute().data

        if existing_att_check:
            st.warning(f"⚠️ Attendance already submitted for this date/subject.")
            st.dataframe(pd.DataFrame(existing_att_check)[['status', 'details']], use_container_width=True)
        else:
            with st.form("attendance_form", clear_on_submit=True):
                payload_att = []
                for student in students_list:
                    col1, col2, col3 = st.columns([2, 2, 3])
                    with col1: 
                        st.markdown(f"**{student['full_name']}**")
                    
                    with col2:
                        status = st.radio(
                            "Status", 
                            ["Present", "Absent", "OD", "Late"], 
                            key=f"status_{student['id']}", 
                            horizontal=True, 
                            label_visibility="collapsed"
                        )
                    
                    with col3:
                        reason_att = "N/A"
                        if status == "Absent":
                            reason_att = st.text_input(
                                "Reason (Informed/Uninformed)", 
                                key=f"res_{student['id']}",
                                placeholder="Type reason here..."
                            )
                        elif status == "OD":
                            reason_att = st.text_input("Event Name", key=f"od_{student['id']}", placeholder="Enter event...")
                        elif status == "Late":
                            t_late = st.time_input("Time", datetime.time(9, 30), key=f"time_{student['id']}")
                            reason_att = str(t_late)
                    
                    payload_att.append({
                        "student_id": student['id'], 
                        "subject_id": subj_id_att, 
                        "date": str(date_sel_att), 
                        "status": status, 
                        "details": reason_att
                    })
                    st.markdown("---")
                
                if st.form_submit_button("✅ Submit Attendance", use_container_width=True, type="primary"):
                    empty_reasons = [p for p in payload_att if p['status'] == "Absent" and not p['details'].strip()]
                    
                    if empty_reasons:
                        st.error("❌ Please provide a reason (Informed/Uninformed) for all Absent students before submitting.")
                    else:
                        try:
                            supabase.table("attendance_logs").insert(payload_att).execute()
                            st.success("🎉 Attendance logged!")
                            st.rerun()
                        except Exception as e: st.error(f"DB Error: {e}")
 
with tab3:
    st.subheader("🤖 AI Student Assistant")
    
    if "current_audit_roll" not in st.session_state:
        st.session_state.current_audit_roll = None
    if "tutor_chat" not in st.session_state:
        st.session_state.tutor_chat = [{"role": "assistant", "content": "Hello! Enter a Roll No to audit."}]

    def handle_audit_selection():
        selection = st.session_state.audit_menu
        if selection != "Choose an option..." and st.session_state.current_audit_roll:
            keyword = "absent dates" if "Absent" in selection else "od dates"
            hist_resp = process_query(f"{keyword} for {st.session_state.current_audit_roll}")
            
            st.session_state.tutor_chat.append({
                "role": "assistant", 
                "content": hist_resp["msg"], 
                "df": hist_resp["content"]
            })
            st.session_state.audit_menu = "Choose an option..."

    # Render History
    for msg in st.session_state.tutor_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "df" in msg and msg["df"] is not None: 
                render_analytics(msg["df"])

    # Chat Input
    if prompt := st.chat_input("Type Roll No or 'clear'..."):
        if prompt.strip().lower() == "clear":
            st.session_state.tutor_chat = [{"role": "assistant", "content": "🗑️ History Cleared."}]
            st.session_state.current_audit_roll = None
            st.rerun()
            
        st.session_state.tutor_chat.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            resp = process_query(prompt, None)
            st.markdown(resp.get("msg", resp["content"]))
            msg_data = {"role": "assistant", "content": resp.get("msg", resp["content"])}
            if resp.get("type") == "dataframe":
                render_analytics(resp["content"])
                msg_data["df"] = resp["content"]
                st.session_state.current_audit_roll = prompt 
            st.session_state.tutor_chat.append(msg_data)
            st.rerun()

    if st.session_state.current_audit_roll:
        st.divider()
        st.markdown(f"🔍 **Quick Audit Tools for Roll No: {st.session_state.current_audit_roll}**")
        
        st.selectbox(
            "Select detailed view:", 
            ["Choose an option...", "📌 View Absent History", "✈️ View OD History"], 
            label_visibility="collapsed", 
            key="audit_menu",
            on_change=handle_audit_selection
        )
# ==========================================
# 🚀 OD APPROVALS TAB (Tutor Level)
# ==========================================
with tab4:
    st.subheader("🚀 Pending OD Requests")
    st.info("Review student OD requests. Approving here will notify the HOD for final sign-off.")

    try:
        # Fetch requests where tutor hasn't decided yet
        # Joins with 'users' table to get the student's name
        pending_ods = supabase.table("od_requests")\
            .select("*, users!od_requests_student_id_fkey(full_name)")\
            .eq("status", "pending")\
            .execute().data

        if pending_ods:
            for req in pending_ods:
                # Use a unique key for each expander/button
                with st.expander(f"OD Request: {req['users']['full_name']} - {req['reason']}"):
                    col_info, col_action = st.columns([2, 1])
                    
                    with col_info:
                        st.write(f"**Reason:** {req['reason']}")
                        st.write(f"**Submitted On:** {req['created_at'][:10]}")
                        if req.get('proof_url'):
                            st.link_button("📄 View Proof (Pamphlet)", req['proof_url'])
                        else:
                            st.warning("No proof uploaded.")

                    with col_action:
                        # Approve sends it to HOD (status -> approved)
                        if st.button("✅ Approve & Forward", key=f"t_app_{req['id']}", use_container_width=True):
                            supabase.table("od_requests")\
                                .update({"status": "approved"})\
                                .eq("id", req['id'])\
                                .execute()
                            st.toast("Approved! Request sent to HOD.")
                            st.rerun()

                        # Reject stops the flow (status -> rejected)
                        if st.button("❌ Reject", key=f"t_rej_{req['id']}", type="primary", use_container_width=True):
                            supabase.table("od_requests")\
                                .update({"status": "rejected"})\
                                .eq("id", req['id'])\
                                .execute()
                            st.toast("OD Request Rejected.")
                            st.rerun()
        else:
            st.success("✨ No pending OD requests for review.")
    except Exception as e:
        st.error(f"Error loading OD requests: {e}")