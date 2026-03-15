import streamlit as st
from utils.db import supabase # Import the shared connection

def login_user(email, password):
    try:
        # 1. Auth with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # 2. Get User Details
        user_id = auth_response.user.id
        access_token = auth_response.session.access_token

        # 3. Get Role & Name
        data_response = supabase.table('users').select('id, email, role, full_name').eq('id', user_id).execute()

        if data_response.data:
            return data_response.data[0], access_token
        else:
            return None, None

    except Exception as e:
        print(f"Login Error: {e}")
        return None, None