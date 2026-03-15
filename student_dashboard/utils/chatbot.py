# import re
# import pandas as pd
# from utils.db import supabase

# def is_valid_uuid(val):
#     """Checks if the input string is a valid UUID."""
#     regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
#     return bool(re.match(regex, val.lower()))

# def process_query(user_input, specific_student_id=None):
#     """
#     Smart query handler that avoids UUID crashes.
#     """
#     clean_input = user_input.lower()
#     found_student = None

#     # --- 1. IDENTIFY THE STUDENT ---
    
#     # CASE A: Student is logged in (ID is provided directly)
#     if specific_student_id:
#         response = supabase.table("users").select("*").eq("id", specific_student_id).execute()
#         if response.data:
#             found_student = response.data[0]
            
#     # CASE B: Tutor/HOD is searching (We need to find the student first)
#     else:
#         # Extract potential search term (Look for digits like "1", "101")
#         match = re.search(r'\b\d+\b', clean_input)
        
#         if not match:
#              # If no number found, ask for clarification
#             return {
#                 "type": "text", 
#                 "content": "⚠️ Please type a Roll Number (e.g. '1' or '101')."
#             }
        
#         search_term = match.group()
        
#         # --- THE FIX FOR THE UUID CRASH ---
#         # We assume "1" is a Roll Number, NOT a UUID.
#         try:
#             # 1. Try finding by Roll No (TEXT column)
#             res = supabase.table("users").select("*").eq("roll_no", search_term).execute()
            
#             # 2. If valid UUID, try finding by ID
#             if not res.data and is_valid_uuid(search_term):
#                 res = supabase.table("users").select("*").eq("id", search_term).execute()

#             if res.data:
#                 found_student = res.data[0]
#             else:
#                 return {
#                     "type": "text", 
#                     "content": f"❌ No student found with Roll No '{search_term}'. (Make sure you added 'roll_no' to the database users table!)"
#                 }
                
#         except Exception as e:
#             return {"type": "text", "content": f"Database Search Error: {e}"}

#     # --- 2. FETCH DATA IF STUDENT FOUND ---
#     if not found_student:
#          return {"type": "text", "content": "❌ Student not found."}
        
#     student_id = found_student['id']
#     student_name = found_student['full_name']

#     # Fetch Marks
#     try:
#         response = supabase.table("performance")\
#             .select("marks, attendance, subjects(name)")\
#             .eq("student_id", student_id)\
#             .execute()
            
#         if response.data:
#             # Clean Data for Display
#             flat_data = []
#             for item in response.data:
#                 subj = item['subjects']['name'] if item.get('subjects') else "Unknown Subject"
#                 flat_data.append({
#                     "Subject": subj,
#                     "Marks": item['marks'],
#                     "Attendance": item.get('attendance', 0)
#                 })
            
#             df = pd.DataFrame(flat_data)
#             return {
#                 "type": "dataframe", 
#                 "content": df, 
#                 "msg": f"📊 **{student_name}** (Roll No: {found_student.get('roll_no', 'N/A')})"
#             }
#         else:
#             return {"type": "text", "content": f"📭 Student **{student_name}** found, but no marks entered yet."}

#     except Exception as e:
#         return {"type": "text", "content": f"Error fetching marks: {e}"}


# chatbot in menu
import re
import pandas as pd
from utils.db import supabase

def is_valid_uuid(val):
    regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(regex, val.lower()))

def process_query(user_input, specific_student_id=None):
    clean_input = user_input.lower()
    found_student = None

    # --- 1. IDENTIFY THE STUDENT ---
    if specific_student_id:
        response = supabase.table("users").select("*").eq("id", specific_student_id).execute()
        if response.data: found_student = response.data[0]
    else:
        match = re.search(r'\b\d+\b', clean_input)
        if not match:
            return {"type": "text", "content": "⚠️ Please type a Roll Number (e.g. '101')."}
        
        search_term = match.group()
        try:
            res = supabase.table("users").select("*").eq("roll_no", search_term).execute()
            if not res.data and is_valid_uuid(search_term):
                res = supabase.table("users").select("*").eq("id", search_term).execute()

            if res.data: found_student = res.data[0]
            else:
                return {"type": "text", "content": f"❌ No student found with Roll No '{search_term}'."}
        except Exception as e:
            return {"type": "text", "content": f"Database Error: {e}"}

    student_id = found_student['id']
    student_name = found_student['full_name']

    # --- 2. NEW FEATURE: DETECT "ABSENT" OR "OD" KEYWORDS ---
    if "absent" in clean_input or "od" in clean_input or "date" in clean_input:
        try:
            # Query the detailed attendance_logs table
            query = supabase.table("attendance_logs").select("date, status, details").eq("student_id", student_id)
            
            if "absent" in clean_input:
                query = query.eq("status", "Absent")
            elif "od" in clean_input:
                query = query.eq("status", "OD")
            
            log_res = query.order("date", desc=True).execute()

            if log_res.data:
                df = pd.DataFrame(log_res.data)
                df.columns = ["Date", "Status", "Details/Reason"]
                return {
                    "type": "dataframe",
                    "content": df,
                    "msg": f"📅 **{student_name}** - Detailed Attendance Log"
                }
            else:
                return {"type": "text", "content": f"✅ No specific Absent/OD logs found for **{student_name}**."}
        except Exception as e:
            return {"type": "text", "content": f"Error fetching logs: {e}"}

    # --- 3. DEFAULT: FETCH PERFORMANCE SUMMARY (Marks & Avg Attendance) ---
    try:
        response = supabase.table("performance")\
            .select("marks, attendance, subjects(name)")\
            .eq("student_id", student_id)\
            .execute()
            
        if response.data:
            flat_data = []
            for item in response.data:
                subj = item['subjects']['name'] if item.get('subjects') else "Unknown"
                flat_data.append({
                    "Subject": subj,
                    "Marks": item['marks'],
                    "Attendance": item.get('attendance', 0)
                })
            
            return {
                "type": "dataframe", 
                "content": pd.DataFrame(flat_data), 
                "msg": f"📊 **{student_name}** (Roll No: {found_student.get('roll_no', 'N/A')})"
            }
        else:
            return {"type": "text", "content": f"📭 No marks entered for **{student_name}**."}

    except Exception as e:
        return {"type": "text", "content": f"Error: {e}"} 