
import streamlit as st
import pandas as pd
from utils.db import supabase
from utils.chatbot import process_query 

st.set_page_config(page_title="HOD Dashboard", layout="wide")


if 'role' not in st.session_state or st.session_state['role'] != 'hod':
    st.error(" ⛔  ACCESS DENIED: This page is for HODs only.")
    st.stop()


with st.sidebar:
    st.title(f"🎓 {st.session_state['user'].get('full_name', 'HOD')}")
    st.info(f"Department: {st.session_state['user'].get('department', 'General')}")
    if st.button("🚪 Logout", type="primary"):
        st.session_state.clear()
        st.switch_page("app.py")

st.title(" 🏆  HOD Dashboard")


tab1, tab2, tab3, tab4 = st.tabs(["📝 Users", "📅 System Approvals", "🤖 AI Student Assistant", "🚀 OD Approvals"])

 
with tab1:
    st.subheader("Manage Department Users")
    try:
        response = supabase.table("users").select("full_name, email, role, department, roll_no").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No users found.")
    except Exception as e:
        st.error(f"Error fetching users: {e}")

 
with tab2:
    st.subheader(" ⚠️  System Alerts & Critical Approvals")
    try:
        reqs = supabase.table("admin_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            request = reqs.data[0]
            req_type = request.get('request_type', 'CLEAR_DB') 
            if req_type == "DELETE_USER":
                target_name = request.get('target_details', 'Unknown User')
                st.warning(f" 🗑️  **APPROVAL REQUEST:** Admin wants to delete user **{target_name}**.")
            else:
                st.error(" 🚨  **URGENT:** Admin has requested a **DATABASE WIPE** for the new semester.")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Request ID:** {request['id']}")
                st.write(f"**Admin Status:** Waiting for HOD & Tutor signatures.")
            with col2:
                if request['hod_approved']:
                    st.success(" ✅  You have already APPROVED this action.")
                else:
                    if st.button(" ✅  APPROVE ACTION", type="primary"):
                        supabase.table("admin_requests").update({"hod_approved": True}).eq("id", request['id']).execute()
                        st.success("Approval recorded.")
                        st.rerun()
        else:
            st.info("No pending high-level approval requests.")
    except Exception as e:
        st.error(f"Error checking requests: {e}")


def render_analytics(df_input):
    if df_input is None or (isinstance(df_input, pd.DataFrame) and df_input.empty): 
        return
    df = df_input.copy()
 
    if "Date" in df.columns and "Status" in df.columns:
        st.subheader("📅 Detailed Attendance History")
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
        col1.metric("⭐ Avg Marks", f"{avg:.1f}")
        if "Attendance" in df.columns:
            col2.metric("📅 Avg Attendance", f"{df['Attendance'].mean():.1f}%")
        
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
        
        st.divider()
        
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📊 Marks Performance")
            st.bar_chart(df.set_index("Subject")["Marks"]) 
        with c2:
            st.subheader("📉 Attendance Stats")
            if "Attendance" in df.columns: 
                st.bar_chart(df.set_index("Subject")["Attendance"], color="#3B82F6")
    
    st.dataframe(df, use_container_width=True)

with tab3:
    st.subheader(" 🔍  Student Analytics Engine")
    
    if "current_audit_roll_hod" not in st.session_state:
        st.session_state.current_audit_roll_hod = None
    if "hod_messages" not in st.session_state:
        st.session_state.hod_messages = [{"role": "assistant", "content": "Enter Roll No or Name to audit student data."}]

     
    def handle_audit_selection_hod():
        selection = st.session_state.audit_menu_hod
        if selection != "Choose an option..." and st.session_state.current_audit_roll_hod:
            keyword = "absent dates" if "Absent" in selection else "od dates"
            hist_resp = process_query(f"{keyword} for {st.session_state.current_audit_roll_hod}")
            
            st.session_state.hod_messages.append({
                "role": "assistant", 
                "content": hist_resp["msg"], 
                "df": hist_resp["content"]
            })
            st.session_state.audit_menu_hod = "Choose an option..."

     
    for msg in st.session_state.hod_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "df" in msg and msg["df"] is not None: 
                render_analytics(msg["df"])

     
    if prompt := st.chat_input("Ex: 'Marks for 101'"):
        if prompt.strip().lower() == "clear":
            st.session_state.hod_messages = [{"role": "assistant", "content": "🗑️ History Cleared."}]
            st.session_state.current_audit_roll_hod = None
            st.rerun()
            
        st.session_state.hod_messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            resp = process_query(prompt)
            st.markdown(resp.get("msg", resp["content"]))
            msg_data = {"role": "assistant", "content": resp.get("msg", resp["content"])}
            
            if resp.get("type") == "dataframe":
                render_analytics(resp["content"])
                msg_data["df"] = resp["content"]
                # Save the roll number for quick audit tools
                st.session_state.current_audit_roll_hod = prompt 
            
            st.session_state.hod_messages.append(msg_data)
            st.rerun()

    
    if st.session_state.current_audit_roll_hod:
        st.divider()
        st.markdown(f"🔍 **Quick Audit Tools for: {st.session_state.current_audit_roll_hod}**")
        
        st.selectbox(
            "Select detailed view:", 
            ["Choose an option...", "📌 View Absent History", "✈️ View OD History"], 
            label_visibility="collapsed", 
            key="audit_menu_hod",
            on_change=handle_audit_selection_hod
        )

with tab4:
    st.subheader("🚀 Final OD Approvals")
    st.info("These requests have been verified by Tutors and require your final authorization.")

    try:
        
        hod_pending = supabase.table("od_requests")\
            .select("*, users!od_requests_student_id_fkey(full_name, roll_no)")\
            .eq("status", "approved")\
            .eq("hod_status", "pending")\
            .execute().data

        if hod_pending:
            for req in hod_pending:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        st.markdown(f"### Student: {req['users']['full_name']} ({req['users']['roll_no']})")
                        st.write(f"**Reason for OD:** {req['reason']}")
                        if req.get('proof_url'):
                            st.link_button("📄 View Student Proof", req['proof_url'])
                    
                    with c2:
                        st.write("🏃 **Tutor Status:** ✅ Approved")
                        
                        
                        if st.button("✅ Final Approve", key=f"hod_app_{req['id']}", use_container_width=True):
                            supabase.table("od_requests")\
                                .update({"hod_status": "approved"})\
                                .eq("id", req['id'])\
                                .execute()
                            st.success(f"OD for {req['users']['full_name']} finalized!")
                            st.rerun()

                        
                        if st.button("❌ Final Reject", key=f"hod_rej_{req['id']}", type="primary", use_container_width=True):
                            supabase.table("od_requests")\
                                .update({"hod_status": "rejected"})\
                                .eq("id", req['id'])\
                                .execute()
                            st.warning("OD Request rejected at HOD level.")
                            st.rerun()
        else:
            st.success("✨ No pending OD requests from Tutors.")
            
    except Exception as e:
        st.error(f"Error loading final approvals: {e}")