# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import uuid
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# ---------- Config / env ----------
TICKETS_CSV = "tickets.csv"
HR_EMAIL = os.getenv("FO_EMAIL")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
HR_DASHBOARD_PASSWORD = os.getenv("FO_DASHBOARD_PASSWORD", None)  # optional

# Folder to store uploaded documents
DOC_FOLDER = "documents"
os.makedirs(DOC_FOLDER, exist_ok=True)

# ---------- Utilities ----------
def generate_ticket_id() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:6].upper()
    return f"TKT-{ts}-{short}"

def load_tickets() -> pd.DataFrame:
    if os.path.exists(TICKETS_CSV):
        df = pd.read_csv(TICKETS_CSV, dtype=str)
        return df
    else:
        cols = [
            "ticket_id", "employee_email", "employee_name", "employee_role",
            "employee_id", "department", "concern", "description", "status",
            "created_at", "closed_at", "last_updated_by"
        ]
        return pd.DataFrame(columns=cols)

def save_tickets(df: pd.DataFrame):
    df.to_csv(TICKETS_CSV, index=False)

def send_email(subject: str, body: str, to_email: str, attachments=None):
    """
    Send email with optional attachments.
    attachments: list of file paths
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        st.warning("Email sender or password not configured. Skipping email send.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.set_content(body)

    # Attach files if provided
    if attachments:
        for file_path in attachments:
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    file_name = os.path.basename(file_path)
                    msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)
            except Exception as e:
                st.warning(f"Failed to attach {file_path}: {e}")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Welcome to FO Ticketing System", page_icon="🎫", layout="wide")
st.title("Welcome to FO Ticketing System")

menu = st.sidebar.selectbox("Choose view", ["Raise a ticket (Employee)", "FO Dashboard"])

# Load existing tickets
tickets_df = load_tickets()

# ------------------- Employee Ticket View -------------------
if menu == "Raise a ticket (Employee)":
    st.header("Raise a new ticket")
    with st.form("ticket_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            employee_email = st.text_input("Employee Email", placeholder="you@company.com")
            employee_name = st.text_input("Employee Name")
            employee_role = st.text_input("Role / Designation")
            employee_id = st.text_input("Employee ID")
        with col2:
            department = st.selectbox("Department",["Support","HR","Fresh Sales","Retention","Pre-Sales","Claims & Legal","Corporate Sales",
                                                    "Marketing","Strategy - Fresh","Lead Gen","Admin","Customer Experience","Founder's Office",
                                                    "Strategy-Retention","MIS-Support","Training","Technology","IT","Finance","Quality & Training",
                                                   ])
            concern = st.selectbox("Concern",
            description = st.text_input("Description / Details")
        submitted = st.form_submit_button("Submit Ticket")

    if submitted:
        # Validate all fields
        if not all([employee_email, employee_name, employee_role, employee_id, department, concern, description]):
            st.error("Please fill all fields.")
        elif "@" not in employee_email:
            st.error("Enter a valid email.")
        else:
            ticket_id = generate_ticket_id()
            now = datetime.now().isoformat(timespec="seconds")
            new_row = {
                "ticket_id": ticket_id,
                "employee_email": employee_email,
                "employee_name": employee_name,
                "employee_role": employee_role,
                "employee_id": employee_id,
                "department": department,
                "concern": concern,
                "description": description,
                "status": "Open",
                "created_at": now,
                "closed_at": "",
                "last_updated_by": employee_email
            }
            tickets_df = pd.concat([tickets_df, pd.DataFrame([new_row])], ignore_index=True)
            save_tickets(tickets_df)
            st.success(f"Ticket created — ID: {ticket_id}")
            st.info("A notification will be sent to FO (if email configured).")

            # Send email to FO
            if HR_EMAIL:
                subject = f"[New FO Ticket] {ticket_id} — {concern}"
                body = f"""A new FO ticket has been raised.

Ticket ID: {ticket_id}
Employee: {employee_name} ({employee_id}) <{employee_email}>
Role: {employee_role}
Department: {department}
Concern: {concern}
Description:
{description}

Created at: {now}
"""
                sent = send_email(subject, body, HR_EMAIL)
                if sent:
                    st.write("FO has been notified by email.")
                else:
                    st.write("Could not send email notification to FO.")
            else:
                st.warning("FO_EMAIL is not configured; HR will not receive email notifications.")

    # Display recent tickets for this employee
    st.markdown("---")
    st.subheader("Your recent tickets")
    if tickets_df.empty:
        st.write("No tickets yet.")
    else:
        if employee_email:
            recent = tickets_df[tickets_df["employee_email"] == employee_email]
            recent = recent.sort_values("created_at", ascending=False).head(10)
            st.dataframe(recent.reset_index(drop=True))
        else:
            st.write("Enter your email above to see your tickets.")


# ------------------- FO Dashboard -------------------
elif menu == "FO Dashboard":
    st.header("FO Dashboard")
    if FO_DASHBOARD_PASSWORD:
        pwd = st.text_input("Enter FO password", type="password")
        if pwd != FO_DASHBOARD_PASSWORD:
            st.warning("Enter password to view dashboard.")
            st.stop()

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        status_filter = st.selectbox("Filter by status", ["All", "Open", "Closed"])
    with col2:
        dept_filter = st.text_input("Filter by department (leave blank = all)")
    with col3:
        empid_filter = st.selectbox(
            "Filter by Employee ID",
            ["All"] + tickets_df.get("employee_id", pd.Series([])).dropna().unique().tolist()
        )
    with col4:
        refresh = st.button("Refresh")

    df = tickets_df.copy()
    if not df.empty:
        if status_filter != "All":
            df = df[df["status"] == status_filter]
        if dept_filter:
            df = df[df["department"].str.contains(dept_filter, case=False, na=False)]
        if empid_filter != "All":
            df = df[df["employee_id"] == empid_filter]

        st.subheader(f"Matching tickets: {len(df)}")
        if len(df) == 0:
            st.write("No tickets match the filters.")
        else:
            # Display tickets
            df_display = df.copy()
            df_display["Emp (ID)"] = df_display["employee_name"] + " (" + df_display["employee_id"] + ")"
            st.dataframe(df_display.sort_values("created_at", ascending=False).reset_index(drop=True))

            # ---------------- Document & Ticket Update ----------------
            # Folder to store documents
            os.makedirs(DOC_FOLDER, exist_ok=True)

            # Select ticket for update
            ticket_to_update = st.selectbox(
                "Select Ticket",
                [f"{row['employee_name']} ({row['employee_id']}) — {row['ticket_id']}" for _, row in df.iterrows()]
            )
            selected_ticket_id = ticket_to_update.split("—")[-1].strip()
            selected_row = df[df["ticket_id"] == selected_ticket_id].iloc[0]

            st.text(f"Selected: {selected_row['employee_name']} ({selected_row['employee_id']}) — {selected_row['ticket_id']}")
            new_status = st.selectbox("Set status", ["Open", "Closed"], index=0 if selected_row["status"]=="Open" else 1)
            hr_note = st.text_area("FO note (optional)")

            # ---------------- Document Management ----------------
            st.subheader("Manage Documents (Max 4 per ticket)")
            ticket_doc_folder = os.path.join(DOC_FOLDER, selected_ticket_id)
            os.makedirs(ticket_doc_folder, exist_ok=True)

            # Existing files with option to delete
            existing_files = os.listdir(ticket_doc_folder)
            files_to_keep = []
            if existing_files:
                st.write("Existing Documents:")
                for f in existing_files:
                    keep = st.checkbox(f"Keep: {f}", value=True, key=f"keep_{f}")
                    if keep:
                        files_to_keep.append(f)
                    else:
                        os.remove(os.path.join(ticket_doc_folder, f))
                        st.info(f"Removed {f}")

            # Upload new files
            max_files = 4
            remaining_slots = max_files - len(files_to_keep)
            uploaded_files = []
            if remaining_slots > 0:
                uploaded_files = st.file_uploader(
                    f"Upload up to {remaining_slots} files",
                    accept_multiple_files=True
                )

            # ---------------- Save Update ----------------
            if st.button("Save update"):
                idx = tickets_df.index[tickets_df["ticket_id"] == selected_ticket_id].tolist()
                if idx:
                    i = idx[0]
                    tickets_df.at[i, "status"] = new_status
                    tickets_df.at[i, "last_updated_by"] = HR_EMAIL or "HR-User"
                    if new_status == "Closed":
                        tickets_df.at[i, "closed_at"] = datetime.now().isoformat(timespec="seconds")
                    save_tickets(tickets_df)

                    # Save uploaded files
                    if uploaded_files:
                        for file in uploaded_files[:remaining_slots]:
                            with open(os.path.join(ticket_doc_folder, file.name), "wb") as f:
                                f.write(file.getbuffer())

                    # Send email to employee with attachments
                    emp_email = tickets_df.at[i, "employee_email"]
                    subject = f"[FO Ticket Update] {selected_ticket_id}"
                    body = f"""Hello {tickets_df.at[i, 'employee_name']},

Your HR ticket {selected_ticket_id} (Concern: {tickets_df.at[i,'concern']}) has been updated.

HR Note:
{hr_note}

Status: {new_status}
Updated at: {datetime.now().isoformat(timespec='seconds')}

Regards,
HR Team
"""
                    # Attach current files
                    files_for_email = os.listdir(ticket_doc_folder)
                    attachments = [os.path.join(ticket_doc_folder, f) for f in files_for_email] if files_for_email else None
                    if send_email(subject, body, emp_email, attachments=attachments):
                        st.success("Ticket updated and employee notified with documents.")
                    else:
                        st.warning("Ticket updated but failed to send email to employee.")

            # ------------------- FO Charts (Only visible to HR) -------------------
            st.markdown("---")
            st.subheader("Ticket Summary Charts")
            if not df.empty:
                # Overall ticket counts
                st.write("### Overall Tickets Count")
                status_counts = df['status'].value_counts()
                st.metric("Total Tickets", len(df))
                st.metric("Open Tickets", status_counts.get("Open", 0))
                st.metric("Closed Tickets", status_counts.get("Closed", 0))

                # Open vs Closed Pie Chart
                st.write("### Open vs Closed Tickets")
                fig_status = px.pie(
                    names=status_counts.index,
                    values=status_counts.values,
                    title="Open vs Closed Tickets",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_status, use_container_width=True)

                # Concern-wise Open/Closed Bar Chart
                st.write("### Concern-wise Open vs Closed Tickets")
                concern_status = df.groupby(['concern', 'status']).size().unstack(fill_value=0)
                
                # Ensure both 'Open' and 'Closed' columns exist
                for status in ["Open", "Closed"]:
                    if status not in concern_status.columns:
                        concern_status[status] = 0
                
                fig_concern = px.bar(
                    concern_status,
                    x=concern_status.index,
                    y=['Open', 'Closed'],
                    title="Concern-wise Open vs Closed Tickets",
                    barmode='group',
                    labels={'value': 'Number of Tickets', 'concern': 'Concern'},
                    color_discrete_map={'Open': 'green', 'Closed': 'red'}
                )
                st.plotly_chart(fig_concern, use_container_width=True)

# ------------------- Sidebar / Footer -------------------
st.sidebar.markdown("---")
st.sidebar.write("App created: Streamlit + pandas\nTicket fields: email, name, role, department, concern, description, employee_id\nData saved to `tickets.csv` and `documents` folder.")
st.sidebar.write("To enable email notifications, set EMAIL_SENDER and EMAIL_PASSWORD env vars (use app passwords for Gmail).")
