
import streamlit as st
from utils.auth import login_user

# --- PAGE CONFIG ---
st.set_page_config(page_title="Academic Performance Insight System", page_icon="🏫", layout="centered")

# --- HELPER: ROLE REDIRECTOR ---
def redirect_to_dashboard(role):
    # 1. FORCE LOWERCASE & REMOVE SPACES
    role_clean = role.lower().strip() 
    
    if role_clean == "hod":
        st.switch_page("pages/01_HOD_Dashboard.py")
    elif role_clean == "tutor":
        st.switch_page("pages/02_Tutor_Dashboard.py")
    elif role_clean == "admin":
        st.switch_page("pages/03_Admin_Dashboard.py")
    elif role_clean == "student":
        # ✅ FIX: Point to the new Dashboard file name
        st.switch_page("pages/04_Student_Dashboard.py")
    else:
        st.error(f"⛔ Role '{role}' not recognized. Please contact support.")
        if st.button("🔄 Reset / Logout"):
            st.session_state.clear()
            st.rerun()

# --- MAIN LOGIC ---

# Check if user is ALREADY logged in
if 'user' in st.session_state:
    redirect_to_dashboard(st.session_state['role'])

# If NOT logged in, show Login Screen
else:
    st.title("Academic Performance Insight System")
    
    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
        
        if submit:
            if email and password:
                user, token = login_user(email, password)
                
                if user:
                    st.session_state['user'] = user
                    st.session_state['token'] = token
                    st.session_state['role'] = user['role']
                    
                    st.success(f"Welcome, {user['full_name']}!")
                    redirect_to_dashboard(user['role'])
                else:
                    st.error("❌ Invalid Email or Password")
            else:
                st.warning("Please enter both email and password.")