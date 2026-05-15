import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import streamlit_js_eval
import time

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
    st.error("❌ No customer data found. Please check your Google Sheet.")
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
            from_row = customer_df[from_mask].iloc[0]
            from_address = from_row.get("address", "Address not found")

    to_mask = customer_df["Name"] == to_location
    to_address = "Address not found"
    if to_mask.any():
        to_row = customer_df[to_mask].iloc[0]
        to_address = to_row.get("address", "Address not found")

    st.text_input("From Address", value=from_address, disabled=True)
    st.text_input("To Address", value=to_address, disabled=True)

# ---------------------------------------------------
# VEHICLE + FIXED GPS (ONLY CHANGE HERE)
# ---------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚗 Vehicle")
    vehicle_numbers = sorted(customer_df["delivery_vh_no"].dropna().unique().tolist())
    selected_vehicle = st.selectbox("Vehicle Number", vehicle_numbers, key="vehicle_unique")

with col2:
    st.subheader("📱 GPS Location")
    
    # ✅ GPS REFRESH BUTTON
    col_refresh, _ = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Refresh GPS", key="gps_refresh", help="Click if GPS not detected"):
            st.rerun()
    
    st.info("👆 Allow location access in browser")
    
    # ✅ UNIVERSAL GPS CODE - 3 FALLBACK STRATEGIES
    location = streamlit_js_eval(
        js_expressions="""
        new Promise((resolve) => {
            // STRATEGY 1: High Accuracy
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                        acc: pos.coords.accuracy || 0
                    }),
                    // STRATEGY 2: Medium Accuracy Fallback
                    () => {
                        navigator.geolocation.getCurrentPosition(
                            (pos) => resolve({
                                lat: pos.coords.latitude,
                                lng: pos.coords.longitude,
                                acc: pos.coords.accuracy || 100
                            }),
                            // STRATEGY 3: Cached Location
                            () => {
                                navigator.geolocation.getCurrentPosition(
                                    (pos) => resolve({
                                        lat: pos.coords.latitude,
                                        lng: pos.coords.longitude,
                                        acc: pos.coords.accuracy || 1000,
                                        cached: true
                                    }),
                                    () => resolve(null),
                                    {maximumAge: 300000, timeout: 5000}
                                );
                            },
                            {timeout: 8000, enableHighAccuracy: false}
                        );
                    },
                    {enableHighAccuracy: true, timeout: 12000, maximumAge: 60000}
                );
            } else {
                resolve(null);
            }
        })
        """,
        key=f"gps_fixed_{int(time.time()//10)}"  # ✅ REFRESHES EVERY 10s OR ON BUTTON
    )

current_location = ""
if location:
    current_lat = location["lat"]
    current_lng = location["lng"]
    current_location = f"{current_lat:.6f},{current_lng:.6f}"
    accuracy = location.get("acc", 0)
    
    col_lat, col_lng, col_acc = st.columns(3)
    with col_lat: st.metric("Lat", f"{current_lat:.6f}")
    with col_lng: st.metric("Lng", f"{current_lng:.6f}")
    with col_acc: st.metric("Accuracy", f"{accuracy:.0f}m")
    
    st.success("✅ GPS Active ✓")
else:
    st.error("❌ Location Access Required")
    st.info("💡 Click **Refresh GPS** or check browser location permission")

# ---------------------------------------------------
# CONTROL BUTTONS
# ---------------------------------------------------
st.markdown("---")
st.subheader("🎮 Trip Controls")

col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🚀 START TRIP", type="primary", use_container_width=True, disabled=not current_location):
        st.session_state.trip_started = True
        st.session_state.start_gps = current_location
        st.success("✅ Travel Started!")
        st.rerun()

with col2:
    if st.button("⏹️ END TRIP", type="secondary", use_container_width=True, disabled=not st.session_state.trip_started):
        if current_location:
            st.session_state.end_gps = current_location
            st.session_state.ready_to_save = True
            st.session_state.trip_started = False
            st.success(f"✅ Arrived at {to_address[:30]}...")
            st.rerun()

# ---------------------------------------------------
# RUNNING ANIMATION
# ---------------------------------------------------
if st.session_state.trip_started:
    st.markdown(f"""
    <div style='text-align:center;padding:40px;background:linear-gradient(135deg,#e3f2fd 0%,#bbdefb 100%);border-radius:20px;margin:20px 0;'>
        <div style='font-size:90px;animation:drive 2s infinite ease-in-out;'>🚚</div>
        <h2 style='color:#1976d2;'>🔄 Trip In Progress</h2>
        <div style='background:white;padding:15px;border-radius:10px;display:inline-block;'>
            <strong>From:</strong> {from_address}<br>
            <strong>To:</strong> {to_address}<br>
            <strong>Vehicle:</strong> {selected_vehicle}
        </div>
    </div>
    <style>
    @keyframes drive {{
        0%,100% {{transform: translateX(0);}}
        50% {{transform: translateX(60px);}}
    }}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# SAVE SECTION
# ---------------------------------------------------
if st.session_state.ready_to_save:
    st.markdown("---")
    st.subheader("💾 Trip Summary")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.success("✅ Trip Completed")
        st.info(f"From: {from_address}")
        st.info(f"To: {to_address}")
        st.info(f"Vehicle: {selected_vehicle}")
    
    with col2:
        if st.button("✅ SAVE TO TRACKER", type="primary", use_container_width=True):
            try:
                end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                map_url = f"https://www.google.com/maps/dir/{st.session_state.start_gps}/{st.session_state.end_gps}"
                
                tracker_sheet.append_row([
                    end_time, selected_vehicle, from_address, to_address,
                    f"{st.session_state.start_gps} → {st.session_state.end_gps}", ""
                ])
                
                last_row = len(tracker_sheet.get_all_values())
                tracker_sheet.update_acell(f"F{last_row}", f'=HYPERLINK("{map_url}","📱 Track Route")')
                
                st.success("✅ Trip Saved Successfully")
                
                for key in ["trip_started", "start_gps", "end_gps", "ready_to_save"]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                init_session_state()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Save failed: {str(e)}")

# ---------------------------------------------------
# STATUS
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

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------
st.markdown("---")
