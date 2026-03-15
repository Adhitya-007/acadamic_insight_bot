import streamlit as st
import pandas as pd
import time
from utils.db import supabase


try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
except KeyError:
    st.error("❌ Configuration Error: Check your secrets.toml file.")
    st.stop()


if 'role' not in st.session_state or st.session_state['role'] != 'admin':
    st.error(" ⛔  ACCESS DENIED: This page is for System Admins only.")
    st.stop()

st.title(" 🛡️  Admin Control Panel")


with st.sidebar:
    st.write(f"👤 **{st.session_state.get('user', {}).get('full_name', 'System Admin')}**")
    if st.button("🚪 Logout", type="primary"):
        st.session_state.clear()
        st.switch_page("app.py")


tab1, tab2, tab3 = st.tabs([" 👤  User Management", " ⚠️  Database Controls", " 📂  View Records"])


with tab1:
    user_action = st.radio("Select Action:", ["Link Single User", "Bulk Upload Profiles"], horizontal=True)
    st.divider()

    
    if user_action == "Link Single User":
        st.subheader("Link New Account")
        st.info("ℹ️  **Workflow:** Create User in Supabase Auth -> Copy UID -> Paste below.")
        
        with st.form("admin_add_user"):
            col1, col2 = st.columns(2)
            with col1:
                new_uid = st.text_input("User UID (Paste from Supabase Auth)")
                new_email = st.text_input("Email Address")
                
                
                dept_list = [
                    "CSE", "CSE(IOT)", "CSE(AIML)", "CSE(CYBER)", 
                    "ECE", "EEE", "MECH", "CIVIL", "MBA", "General"
                ]
                new_dept = st.selectbox("Department", dept_list)
                
            with col2:
                new_name = st.text_input("Full Name")
                new_role = st.selectbox("Role", ["student", "tutor", "hod", "admin"])
                new_roll = st.text_input("Roll No (Required for Students)", placeholder="e.g., 727824tuio001")
            
            if st.form_submit_button("Create Profile"):
                if new_uid and new_email:
                    try:
                        data = {
                            "id": new_uid,
                            "email": new_email,
                            "full_name": new_name,
                            "role": new_role,
                            "department": new_dept 
                        }
                        if new_role == "student" and new_roll:
                            data["roll_no"] = new_roll
                        
                        supabase.table("users").insert(data).execute()
                        st.success(f"✅ Linked {new_name} ({new_dept}) successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("UID and Email are required.")

    
    elif user_action == "Bulk Upload Profiles":
        st.subheader("📂 Bulk Profile Import")
        st.info("Upload CSV with headers: `uid, email, full_name, role, department, roll_no`")

        uploaded_file = st.file_uploader("Upload CSV/Excel", type=['csv', 'xlsx'])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                df.columns = df.columns.str.strip().str.lower()
                
                if st.button("🚀 Import Profiles"):
                    progress = st.progress(0)
                    for i, row in df.iterrows():
                        try:
                            data = {
                                "id": row['uid'],
                                "email": row['email'],
                                "full_name": row['full_name'],
                                "role": row['role'],
                                "department": row.get('department', 'General')
                            }
                            if 'roll_no' in row and pd.notna(row['roll_no']):
                                data['roll_no'] = str(row['roll_no'])
                            
                            supabase.table("users").insert(data).execute()
                        except Exception as e:
                            st.warning(f"Skipped {row['email']}: {e}")
                        progress.progress((i + 1) / len(df))
                    st.success("🎉 Import Complete!")

            except Exception as e:
                st.error(f"File Error: {e}")


with tab2:
    st.subheader("⚠️  Dangerous Actions")
    st.write("All actions require **HOD + Tutor Approval**.")
    
    
    try:
        reqs = supabase.table("admin_requests").select("*").eq("status", "pending").execute()
        pending = reqs.data[0] if reqs.data else None
    except:
        pending = None

    if not pending:
        
        col1, col2 = st.columns(2)
        
        
        with col1:
            st.write("### 🗑️ Delete Specific User")
            users = supabase.table("users").select("id, full_name, email, role").execute()
            user_map = {f"{u['full_name']} ({u['role']})" : u['id'] for u in users.data} if users.data else {}
            
            target_user = st.selectbox("Select User to Remove", list(user_map.keys()))
            
            if st.button("Request User Deletion"):
                target_uid = user_map[target_user]
                supabase.table("admin_requests").insert({
                    "request_type": "DELETE_USER",
                    "status": "pending",
                    "target_id": target_uid,
                    "target_details": target_user,
                    "hod_approved": False, 
                    "tutor_approved": False
                }).execute()
                st.rerun()

        
        with col2:
            st.write("### ☢️ Wipe Semester Data")
            st.write("Clears all marks and attendance.")
            if st.button("Request Full Database Wipe"):
                supabase.table("admin_requests").insert({
                    "request_type": "CLEAR_DB",
                    "status": "pending",
                    "hod_approved": False, 
                    "tutor_approved": False
                }).execute()
                st.rerun()

    else:
    
        st.divider()
        req_type = pending['request_type']
        
        if req_type == "DELETE_USER":
            st.warning(f"⏳ **Request:** Permanently Delete User **{pending['target_details']}**")
        else:
            st.error("⏳ **Request:** WIPE ALL SEMESTER DATA")

        c1, c2 = st.columns(2)
        c1.metric("HOD Approval", "✅ Yes" if pending['hod_approved'] else "❌ Waiting")
        c2.metric("Tutor Approval", "✅ Yes" if pending['tutor_approved'] else "❌ Waiting")
        
        
        if pending['hod_approved'] and pending['tutor_approved']:
            st.success("✅ Approvals Received.")
            
            if st.button("🔥 EXECUTE APPROVED ACTION"):
                try:
                    if req_type == "CLEAR_DB":
                        supabase.rpc("wipe_semester_data").execute()
                        st.success("Database Wiped.")
                        
                    elif req_type == "DELETE_USER":
                        
                        target = pending['target_id']
                        supabase.table("users").delete().eq("id", target).execute()
                        st.success(f"User {pending['target_details']} deleted.")

                    
                    supabase.table("admin_requests").update({"status": "completed"}).eq("id", pending['id']).execute()
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Execution Failed: {e}")


with tab3:
    st.subheader("📂 Database Records")
    view_option = st.selectbox("Select Table", ["All Users", "Student Marks"])
    
    if view_option == "All Users":
        data = supabase.table("users").select("full_name, email, role, department, roll_no").execute()
        if data.data:
            st.dataframe(pd.DataFrame(data.data), use_container_width=True)
    else:
        data = supabase.table("performance").select("*, users(full_name, department)").execute()
        if data.data:
            st.dataframe(pd.json_normalize(data.data), use_container_width=True)