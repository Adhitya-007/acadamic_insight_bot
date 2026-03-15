###without duplicate
import streamlit as st
import pandas as pd
import time
from utils.db import supabase

st.set_page_config(page_title="Student Dashboard", page_icon="🎓", layout="wide")

if 'user' not in st.session_state or st.session_state['role'] != 'student':
    st.warning("⛔ Please login as a student.")
    st.stop()

user_id = st.session_state['user']['id']

st.title("🎓 Student Performance & OD Portal")


try:
    perf = supabase.table("performance").select("marks, attendance, subjects(name)").eq("student_id", user_id).execute().data
    if perf:
        df = pd.DataFrame([{"Subject": i['subjects']['name'], "Marks": i['marks'], "Attendance": i['attendance']} for i in perf])
        m1, m2, m3 = st.columns(3)
        m1.metric("📚 Subjects", len(df))
        m2.metric("📊 Avg Marks", f"{df['Marks'].mean():.1f}")
        m3.metric("📅 Attendance", f"{df['Attendance'].mean():.1f}%")
        st.bar_chart(df.set_index("Subject")[["Marks", "Attendance"]])
except Exception as e:
    st.error(f"Error loading performance: {e}")


st.divider()
col_form, col_status = st.columns(2)

with col_form:
    st.subheader("🚀 New OD Request")
    with st.form("od_form", clear_on_submit=True):
        reason = st.text_input("Reason (Event/Activity)")
        file = st.file_uploader("Upload Proof", type=['png', 'jpg', 'pdf'])
        if st.form_submit_button("Submit Request"):
            if reason and file:
                try:
                    # Added timestamp to prevent 409 Duplicate error
                    path = f"{user_id}/{int(time.time())}_{file.name}"
                    supabase.storage.from_("od-proofs").upload(path, file.read())
                    url = supabase.storage.from_("od-proofs").get_public_url(path)
                    
                    supabase.table("od_requests").insert({
                        "student_id": user_id, "reason": reason, "proof_url": url,
                        "status": "pending", "hod_status": "pending"
                    }).execute()
                    st.success("✅ Submitted to Tutor!")
                except Exception as e: st.error(f"Error: {e}")

with col_status:
    st.subheader("📂 My OD Status")
    # Change 'status' to 'tutor_status'
    history = supabase.table("od_requests").select("reason, tutor_status, hod_status").eq("student_id", user_id).execute().data
    if history:
        # Updated rename key to match the new query column
        st.dataframe(pd.DataFrame(history).rename(columns={"tutor_status": "Tutor", "hod_status": "HOD"}), use_container_width=True)