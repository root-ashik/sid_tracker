import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import streamlit_js_eval

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Delivery Tracking System",
    layout="wide",
    page_icon="🚚"
)

st.title("🚚 Delivery Tracking System")
st.markdown("---")

# ---------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------
@st.cache_resource
def init_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        scope
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key("1Cwe5jN7iiNYV9LKReshFl_BLvcuAJ3pgMeWBWaRstCY")
    return spreadsheet.worksheet("Cus_Details"), spreadsheet.worksheet("Tracker")

customer_sheet, tracker_sheet = init_sheets()

# ---------------------------------------------------
# LOAD CUSTOMER DATA
# ---------------------------------------------------
@st.cache_data
def load_customer_data():
    customer_data = customer_sheet.get_all_records()
    customer_df = pd.DataFrame(customer_data)
    customer_df.columns = customer_df.columns.str.strip()
    return customer_df

customer_df = load_customer_data()

if customer_df.empty:
    st.error("❌ No customer data found.")
    st.stop()

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
def init_session_state():
    defaults = {
        "trip_started": False,
        "start_gps": "",
        "end_gps": "",
        "ready_to_save": False
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ---------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("📍 Locations")
    location_names = ["Office"] + customer_df["Name"].dropna().tolist()
    from_location = st.selectbox("From", location_names, key="from_location_unique")
    to_location = st.selectbox("To", customer_df["Name"].dropna().tolist(), key="to_location_unique")

with col2:
    st.subheader("📋 Addresses")
    
    from_address = "Office"
    if from_location != "Office":
        from_mask = customer_df["Name"] == from_location
        if from_mask.any():
            from_address = customer_df[from_mask].iloc[0].get("address", "N/A")
    
    to_mask = customer_df["Name"] == to_location
    to_address = "N/A"
    if to_mask.any():
        to_address = customer_df[to_mask].iloc[0].get("address", "N/A")
    
    st.text_input("From Address", value=from_address, disabled=True)
    st.text_input("To Address", value=to_address, disabled=True)

# ---------------------------------------------------
# VEHICLE + GPS
# ---------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚗 Vehicle")
    vehicle_numbers = sorted(customer_df["delivery_vh_no"].dropna().unique().tolist())
    selected_vehicle = st.selectbox("Vehicle Number", vehicle_numbers, key="vehicle_unique")

with col2:
    st.subheader("📱 GPS Location")
    st.info("👆 Allow location access")
    
    location = streamlit_js_eval(
        js_expressions="""
        new Promise((resolve) => {
            if (!navigator.geolocation) return resolve(null);
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                }),
                () => resolve(null),
                {enableHighAccuracy: true, timeout: 10000}
            );
        })
        """,
        key=f"gps_location_{int(datetime.now().timestamp())}"  # ✅ UNIQUE KEY FIX
    )

current_location = ""
if location:
    current_lat = location["latitude"]
    current_lng = location["longitude"]
    current_location = f"{current_lat:.6f},{current_lng:.6f}"
    accuracy = location.get("accuracy", 0)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Lat", f"{current_lat:.6f}")
    with col2: st.metric("Lng", f"{current_lng:.6f}")
    with col3: st.metric("Accuracy", f"{accuracy:.0f}m")
    st.success("✅ GPS Active")
else:
    st.error("❌ Location Access Required")

# ---------------------------------------------------
# CONTROL BUTTONS
# ---------------------------------------------------
st.markdown("---")
st.subheader("🎮 Trip Controls")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 START TRIP", type="primary", use_container_width=True, disabled=not current_location):
        st.session_state.trip_started = True
        st.session_state.start_gps = current_location
        st.rerun()

with col2:
    if st.button("⏹️ END TRIP", type="secondary", use_container_width=True, disabled=not st.session_state.trip_started):
        if current_location:
            st.session_state.end_gps = current_location
            st.session_state.ready_to_save = True
            st.session_state.trip_started = False
            st.rerun()

# ---------------------------------------------------
# ✅ FIXED RUNNING ANIMATION - SEPARATE CSS BLOCK
# ---------------------------------------------------
if st.session_state.trip_started:
    st.markdown("""
    <style>
    @keyframes truck_drive {
        0% { transform: translateX(-50px) rotate(-2deg); }
        25% { transform: translateX(0px) rotate(1deg); }
        50% { transform: translateX(50px) rotate(0deg); }
        75% { transform: translateX(25px) rotate(-1deg); }
        100% { transform: translateX(-50px) rotate(-2deg); }
    }
    .truck-animation {
        font-size: 100px !important;
        display: block !important;
        animation: truck_drive 3s infinite ease-in-out !important;
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='
        text-align: center;
        padding: 40px;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 20px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    '>
        <div class='truck-animation'>🚚</div>
        <h2 style='color: #1976d2; margin: 20px 0;'>🔄 TRIP IN PROGRESS</h2>
        <div style='
            background: white;
            padding: 20px;
            border-radius: 15px;
            display: inline-block;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        '>
            <strong>📍 From:</strong> {from_address[:60]}<br>
            <strong>📍 To:</strong> {to_address[:60]}<br>
            <strong>🚗 Vehicle:</strong> {selected_vehicle}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# SAVE SECTION
# ---------------------------------------------------
if st.session_state.ready_to_save:
    st.markdown("---")
    st.subheader("💾 Confirm Trip")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ Trip Completed Successfully!")
        st.info(f"**Route:** {from_address}")
        st.info(f"**Destination:** {to_address}")
        st.info(f"**Vehicle:** {selected_vehicle}")
        st.info(f"**GPS:** {st.session_state.start_gps} → {st.session_state.end_gps}")
    
    with col2:
        if st.button("✅ SAVE TO TRACKER SHEET", type="primary", use_container_width=True):
            try:
                end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                map_url = f"https://www.google.com/maps/dir/{st.session_state.start_gps}/{st.session_state.end_gps}"
                
                # Save data
                tracker_sheet.append_row([
                    end_time,
                    selected_vehicle,
                    from_address,
                    to_address,
                    f"{st.session_state.start_gps} → {st.session_state.end_gps}",
                    ""
                ])
                
                # Add track link
                last_row = len(tracker_sheet.get_all_values())
                tracker_sheet.update_acell(f"F{last_row}", f'=HYPERLINK("{map_url}","📱 Track")')
                
                # ✅ SUCCESS VEHICLE ANIMATION
                st.markdown("""
                <style>
                @keyframes truck_celebrate {
                    0%, 100% { transform: scale(1) rotate(0deg); }
                    25% { transform: scale(1.1) rotate(10deg); }
                    50% { transform: scale(1.3) rotate(0deg); }
                    75% { transform: scale(1.1) rotate(-10deg); }
                }
                .success-truck {
                    font-size: 120px !important;
                    animation: truck_celebrate 2s infinite !important;
                    text-align: center !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown("""
                <div style='
                    text-align: center;
                    padding: 40px;
                    background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%);
                    border-radius: 25px;
                    margin: 20px 0;
                    box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                '>
                    <div class='success-truck'>🚚✅</div>
                    <h1 style='color: #2e7d32; margin: 20px 0;'>🎉 TRIP SAVED!</h1>
                    <p style='font-size: 20px; color: #388e3c;'>Successfully recorded in Tracker sheet</p>
                    <div style='margin-top: 20px;'>
                        <a href='https://www.google.com/maps/dir/START/END' target='_blank' 
                           style='
                            display: inline-block;
                            padding: 15px 30px;
                            background: #4caf50;
                            color: white;
                            text-decoration: none;
                            border-radius: 25px;
                            font-weight: bold;
                            font-size: 18px;
                            box-shadow: 0 5px 15px rgba(76,175,80,0.4);
                        '>📱 View Route on Maps</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Reset state
                for key in ["trip_started", "start_gps", "end_gps", "ready_to_save"]:
                    if key in st.session_state:
                        del st.session_state[key]
                init_session_state()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Save failed: {str(e)}")

# ---------------------------------------------------
# STATUS & RESET
# ---------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Reset All", type="secondary", use_container_width=True):
        for key in ["trip_started", "start_gps", "end_gps", "ready_to_save"]:
            if key in st.session_state:
                del st.session_state[key]
        init_session_state()
        st.rerun()

with col2:
    gps_status = "🟢 Active" if current_location else "🔴 Disabled"
    trip_status = "🟡 In Progress" if st.session_state.trip_started else "⚪ Ready"
    st.metric("GPS", gps_status)
    st.metric("Trip", trip_status)

st.markdown("---")
st.caption("👨‍💼 Delivery Tracking System | Powered by Streamlit")
