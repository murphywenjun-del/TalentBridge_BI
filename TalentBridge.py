import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px 

# 1. Page Configuration
st.set_page_config(page_title="TalentBridge BI Pro", layout="wide", page_icon="📈")
st.title("Bridge the Gap: TalentBridge End-to-End Penetration & Compliance Audit System")

# 2. Database Connection
def get_connection():
    return sqlite3.connect('talentbridge.db')

conn = get_connection()

# 3. Sidebar: Global Decision Dimensions
with st.sidebar:
    st.header("⚙️ Core Decision Dimensions")
    month_options = ["All Months", "2024-04", "2024-05", "2024-06", "2024-10", "2025-01", "2025-03"]
    selected_month = st.selectbox("Business Month", month_options)
    
    try:
        city_df = pd.read_sql_query("SELECT city_id, name FROM CITY", conn)
        city_options = ["All Cities"] + list(city_df['name'].unique())
    except:
        city_options = ["All Cities"]
    selected_city = st.selectbox("Business Region", city_options)

    city_id_val = None
    if selected_city != "All Cities":
        city_id_val = city_df[city_df['name'] == selected_city]['city_id'].values[0]

    def get_time_filter(col_name):
        return f" AND {col_name} LIKE '{selected_month}%' " if selected_month != "All Months" else ""

tab_perf, tab_audit, tab_console = st.tabs(["📊 Business Dashboard", "✨ Intelligent Audit Assistant", "💻 SQL Console"])

# --- Tab 1: Business Dashboard ---
with tab_perf:
    st.subheader(f"📊 Business Analysis: {selected_month} | {selected_city}")
    c_filter_e = f" AND e.city_id = {city_id_val} " if city_id_val else ""
    
    # 1.1 Penetration Funnel
    funnel_sql = f"""
    SELECT '1. Total Calls' as Stage, COUNT(*) as Count FROM TELE_OUTREACH t 
    JOIN ENROLLMENT e ON t.candidate_id = e.candidate_id 
    WHERE 1=1 {get_time_filter('t.call_date')} {c_filter_e}
    UNION ALL
    SELECT '2. Interviews' as Stage, COUNT(*) as Count FROM HR_INTERVIEW i 
    JOIN ENROLLMENT e ON i.candidate_id = e.candidate_id 
    WHERE 1=1 {get_time_filter('i.interview_date')} {c_filter_e}
    UNION ALL
    SELECT '3. Placed Success' as Stage, COUNT(*) as Count FROM PLACEMENT p 
    JOIN ENROLLMENT e ON p.enrollment_id = e.enrollment_id 
    WHERE 1=1 {get_time_filter('p.employment_date')} {c_filter_e}
    """
    st.plotly_chart(px.funnel(pd.read_sql_query(funnel_sql, conn), x='Count', y='Stage', title="Penetration Conversion Funnel"), use_container_width=True)

    st.markdown("---")
    col_pie, col_tele, col_int = st.columns([1, 1, 1])
    
    with col_pie:
        st.write("📂 **Interview Status Distribution**")
        status_sql = f"SELECT i.interview_status, COUNT(*) as Count FROM HR_INTERVIEW i JOIN ENROLLMENT e ON i.candidate_id = e.candidate_id WHERE 1=1 {get_time_filter('i.interview_date')} {c_filter_e} GROUP BY 1"
        try: st.plotly_chart(px.pie(pd.read_sql_query(status_sql, conn), values='Count', names='interview_status', hole=.4), use_container_width=True)
        except: pass

    with col_tele:
        st.write("📞 **Tele-Marketing Performance (Region/Time Linked)**")
        tele_perf_sql = f"SELECT s.name, COUNT(t.call_id) AS Total, SUM(CASE WHEN t.outcome LIKE '%Interested%' THEN 1 ELSE 0 END) AS Success FROM HR_STAFF s JOIN TELE_OUTREACH t ON s.staff_id = t.staff_id JOIN ENROLLMENT e ON t.candidate_id = e.candidate_id WHERE 1=1 {get_time_filter('t.call_date')} {c_filter_e} GROUP BY 1 ORDER BY Success DESC"
        st.dataframe(pd.read_sql_query(tele_perf_sql, conn), use_container_width=True)

    with col_int:
        st.write("👨‍🏫 **Interviewer Performance (Region/Time Linked)**")
        int_perf_sql = f"SELECT s.name, COUNT(i.interview_id) AS Total, SUM(CASE WHEN i.interview_status IN ('Passed', 'Completed') THEN 1 ELSE 0 END) AS Success FROM HR_STAFF s JOIN HR_INTERVIEW i ON s.staff_id = i.staff_id JOIN ENROLLMENT e ON i.candidate_id = e.candidate_id WHERE 1=1 {get_time_filter('i.interview_date')} {c_filter_e} GROUP BY 1 ORDER BY Success DESC"
        st.dataframe(pd.read_sql_query(int_perf_sql, conn), use_container_width=True)

    st.markdown("---")
    
    # 🌟 1.3 Core: Detailed Placement Audit (Including No-Interview High Attention Logic)
    st.subheader("🎓 Detailed Placement Path Audit (Compliance Risk Version)")
    detail_sql = f"""
    SELECT 
        c.first_name || ' ' || c.last_name AS Student,
        p.employment_date AS Placed_Date,
        ci.name AS City,
        COUNT(DISTINCT t.call_id) AS Calls,
        COUNT(DISTINCT i.interview_id) AS Intvs,
        CASE 
            WHEN COUNT(DISTINCT i.interview_id) = 0 THEN '🚨 Severe Audit Risk: Placed without Interview'
            WHEN COUNT(DISTINCT t.call_id) = 1 AND COUNT(DISTINCT i.interview_id) = 1 THEN '✅ Standard Efficient Path'
            WHEN COUNT(DISTINCT t.call_id) = 0 AND COUNT(DISTINCT i.interview_id) = 1 THEN '⭐ Premium Direct Path'
            WHEN COUNT(DISTINCT t.call_id) > 2 THEN '🚩 Warning: High Communication Cost'
            WHEN COUNT(DISTINCT i.interview_id) > 1 THEN '⚠️ Warning: Multiple Interview Rounds'
            ELSE '✅ Path Meets Expectations'
        END AS Detailed_Audit_Result
    FROM PLACEMENT p 
    JOIN ENROLLMENT e ON p.enrollment_id = e.enrollment_id 
    JOIN CANDIDATE c ON e.candidate_id = c.candidate_id 
    JOIN CITY ci ON e.city_id = ci.city_id
    LEFT JOIN TELE_OUTREACH t ON c.candidate_id = t.candidate_id 
    LEFT JOIN HR_INTERVIEW i ON c.candidate_id = i.candidate_id
    WHERE 1=1 {get_time_filter('p.employment_date')} {c_filter_e}
    GROUP BY p.placement_id
    ORDER BY (COUNT(DISTINCT i.interview_id) = 0) DESC, Calls DESC
    """
    df_detail = pd.read_sql_query(detail_sql, conn)
    # Color coding for severe risks
    st.dataframe(df_detail.style.applymap(
        lambda x: 'background-color: #ff4b4b; color: white;' if '🚨' in str(x) else 
                  ('background-color: #ffcc00;' if '🚩' in str(x) or '⚠️' in str(x) else ''),
        subset=['Detailed_Audit_Result']
    ), use_container_width=True)

# --- Tab 2: Audit Assistant (Finance 7 Attributes + Retention Chart + Blacklist) ---
with tab_audit:
    st.subheader("🤖 Management Decision Audit Module")
    task = st.selectbox("Select Project", ["Overdue Invoices Audit (7 Attributes)", "City Retention Analysis (With Chart)", "Ghosted Blacklist (No Show)"])
    
    if task == "Overdue Invoices Audit (7 Attributes)":
        sql = f"""
        SELECT can.first_name || ' ' || can.last_name AS Name, can.phone, p.employment_date, pp.plan_type, 
               COALESCE(i.amount_paid, 0) AS Paid, (i.amount_due - COALESCE(i.amount_paid, 0)) AS Balance, 
               i.amount_due AS Total, i.due_date
        FROM INSTALLMENT i
        JOIN PLACEMENT p ON i.placement_id = p.placement_id
        JOIN ENROLLMENT e ON p.enrollment_id = e.enrollment_id
        JOIN CANDIDATE can ON e.candidate_id = can.candidate_id
        JOIN PAYMENT_PLAN pp ON p.plan_id = pp.plan_id
        WHERE i.due_date <= date('now') AND (i.amount_paid < i.amount_due OR i.amount_paid IS NULL)
        {get_time_filter('p.employment_date')} {c_filter_e}
        ORDER BY Balance DESC
        """
        df_fin = pd.read_sql_query(sql, conn)
        st.dataframe(df_fin, use_container_width=True)
        st.metric("Total Risk Debt Exposure", f"${df_fin['Balance'].sum():,.2f}")

    elif task == "City Retention Analysis (With Chart)":
        # 🌟 Link Global Dimensions: Time (Based on Arrival Date) and Location
        t_filter_ol = get_time_filter('ol.arrival_date')
        c_filter_ci = f" AND ci.city_id = {city_id_val} " if city_id_val else ""

        # Core SQL: Calculate total onboarded vs currently active for specific time/location
        sql = f"""
        SELECT 
            ci.name as City, 
            COUNT(DISTINCT ol.onboard_id) as Total_Onboarded,
            SUM(CASE WHEN e.enrollment_status = 'Active' THEN 1 ELSE 0 END) as Currently_Active,
            ROUND(CAST(SUM(CASE WHEN e.enrollment_status = 'Active' THEN 1 ELSE 0 END) AS FLOAT) / 
            NULLIF(COUNT(DISTINCT ol.onboard_id), 0) * 100, 2) AS Retention_Rate
        FROM CITY ci 
        LEFT JOIN ONBOARDING_LOG ol ON ci.city_id = ol.city_id 
        LEFT JOIN ENROLLMENT e ON ol.candidate_id = e.candidate_id
        WHERE 1=1 {t_filter_ol} {c_filter_ci}
        GROUP BY ci.name
        HAVING Total_Onboarded > 0
        """
        
        try:
            df_ret = pd.read_sql_query(sql, conn)
            
            if not df_ret.empty:
                st.write(f"🏙️ **{selected_month} | {selected_city} Post-Onboarding Retention Performance**")
                
                # Plot Chart: Use gradient colors and label values
                fig = px.bar(
                    df_ret, 
                    x='City', 
                    y='Retention_Rate', 
                    color='Retention_Rate',
                    text='Retention_Rate',
                    title=f"City-wise Student Retention Analysis (%) - {selected_month}",
                    color_continuous_scale='GnBu',
                    labels={'Retention_Rate': 'Retention Rate (%)'}
                )
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Show detailed table for audit support
                st.dataframe(df_ret, use_container_width=True)
            else:
                st.info(f"📅 No onboarding data found for the selected criteria ({selected_month}), please switch months.")
        except Exception as e:
            st.error(f"Failed to load retention chart. Error: {e}")
            st.info("💡 Tip: If a column is not found, run `PRAGMA table_info(ONBOARDING_LOG);` in the console to verify the date column name.")
            
    elif task == "Ghosted Blacklist (No Show)":
        # Core Logic: Interview Passed + (City determined via Enrollment or Placement) + Onboarding missing
        c_filter = f" AND e.city_id = {city_id_val} " if city_id_val else ""
        
        sql = f"""
        SELECT 
            c.first_name || ' ' || c.last_name AS Student, 
            c.phone, 
            COALESCE(ci.name, 'Pending/Unassigned') AS Target_City, 
            i.interview_status AS Intv_Status,
            '🚫 Ghosted' AS Risk_Status
        FROM HR_INTERVIEW i 
        JOIN CANDIDATE c ON i.candidate_id = c.candidate_id 
        -- Use LEFT JOIN Enrollment to avoid missing ghosted candidates who passed interview but didn't complete enrollment
        LEFT JOIN ENROLLMENT e ON c.candidate_id = e.candidate_id 
        LEFT JOIN CITY ci ON e.city_id = ci.city_id 
        -- Core: Find those who are missing from onboarding logs
        LEFT JOIN ONBOARDING_LOG ol ON c.candidate_id = ol.candidate_id
        WHERE i.interview_status IN ('Passed', 'Completed') 
          AND ol.onboard_id IS NULL 
          {get_time_filter('i.interview_date')} 
          {c_filter}
        """
        df_ghost = pd.read_sql_query(sql, conn)
        st.write(f"🔍 Audit Result: Found {len(df_ghost)} students who passed interview but did not show up")
        st.dataframe(df_ghost, use_container_width=True)

# --- Tab 3: Console ---
with tab_console:
    st.subheader("💻 Cross-Table Penetration Console")
    user_sql = st.text_area("Enter SQL to perform penetration demo:", value="SELECT * FROM CANDIDATE LIMIT 5;")
    if st.button("▶️ Run Query"):
        try: st.dataframe(pd.read_sql_query(user_sql, conn), use_container_width=True)
        except Exception as e: st.error(e)