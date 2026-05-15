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
    page_icon="📱"
)

st.title("📱🚚 Delivery Tracking System")
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
        "ready_to_save": False,
        "gps_attempts": 0
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ---------------------------------------------------
# 🌍 UNIVERSAL GPS FUNCTION - WORKS ON ALL DEVICES
# ---------------------------------------------------
def get_gps_location():
    """Universal GPS getter for all devices/browsers"""
    # ✅ MULTIPLE GPS STRATEGIES
    gps_code = """
    new Promise((resolve) => {
        // Strategy 1: High Accuracy (Mobile preferred)
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    resolve({
                        method: 'high_accuracy',
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy: pos.coords.accuracy || 0,
                        timestamp: Date.now()
                    });
                },
                // Fallback Strategy 2: Medium Accuracy
                () => {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {
                            resolve({
                                method: 'medium_accuracy',
                                latitude: pos.coords.latitude,
                                longitude: pos.coords.longitude,
                                accuracy: pos.coords.accuracy || 999,
                                timestamp: Date.now()
                            });
                        },
                        // Fallback Strategy 3: Cached/Old location
                        () => {
                            navigator.geolocation.getCurrentPosition(
                                (pos) => {
                                    resolve({
                                        method: 'cached',
                                        latitude: pos.coords.latitude,
                                        longitude: pos.coords.longitude,
                                        accuracy: pos.coords.accuracy || 9999,
                                        timestamp: pos.timestamp || Date.now(),
                                        cached: true
                                    });
                                },
                                // Final fallback
                                () => resolve(null),
                                {maximumAge: 600000, timeout: 5000, enableHighAccuracy: false}
                            );
                        },
                        {timeout: 8000, enableHighAccuracy: false}
                    );
                },
                {enableHighAccuracy: true, timeout: 10000, maximumAge: 300000}
            );
        } else {
            resolve(null);
        }
    })
    """
    return streamlit_js_eval(
        js_expressions=gps_code,
        key=f"gps_universal_{st.session_state.get('gps_attempts', 0)}_{int(time.time())}"
    )

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
# VEHICLE + SUPER GPS
# ---------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚗 Vehicle")
    vehicle_numbers = sorted(customer_df["delivery_vh_no"].dropna().unique().tolist())
    selected_vehicle = st.selectbox("Vehicle Number", vehicle_numbers, key="vehicle_unique")

with col2:
    st.subheader("🌍 GPS Location")
    
    # ✅ REFRESH GPS BUTTON
    col_gps1, col_gps2 = st.columns(2)
    with col_gps1:
        if st.button("📡 Refresh GPS", type="secondary"):
            st.session_state.gps_attempts = st.session_state.get("gps_attempts", 0) + 1
            st.rerun()
    
    # ✅ UNIVERSAL GPS CALL
    location = get_gps_location()
    
    current_location = ""
    if location:
        method = location.get("method", "unknown")
        lat = location["latitude"]
        lng = location["longitude"]
        accuracy = location.get("accuracy", 999)
        cached = location.get("cached", False)
        
        current_location = f"{lat:.6f},{lng:.6f}"
        
        # ✅ GPS STATUS DISPLAY
        if cached:
            st.warning(f"📡 GPS ({method}): Cached location")
        elif accuracy < 20:
            st.success(f"📡 GPS ({method}): Excellent ({accuracy}m)")
        elif accuracy < 100:
            st.info(f"📡 GPS ({method}): Good ({accuracy}m)")
        else:
            st.warning(f"📡 GPS ({method}): {accuracy}m")
        
        # ✅ METRICS
        col1m, col2m, col3m = st.columns(3)
        with col1m: st.metric("Latitude", f"{lat:.6f}")
        with col2m: st.metric("Longitude", f"{lng:.6f}")
        with col3m: st.metric("Accuracy", f"{accuracy:.0f}m")
        
    else:
        st.error("❌ No GPS Signal")
        st.info("""
        **📱 Troubleshooting:**
        1. Click **Refresh GPS** button
        2. Allow location in browser popup
        3. Check location icon 🔵 in address bar
        4. Try different browser (Chrome/Firefox best)
        5. Enable GPS on mobile
        """)

# ---------------------------------------------------
# CONTROL BUTTONS
# ---------------------------------------------------
st.markdown("---")
st.subheader("🎮 Trip Controls")

col1, col2 = st.columns(2)

with col1:
    start_disabled = not current_location or st.session_state.trip_started
    if st.button("🚀 START TRIP", type="primary", use_container_width=True, disabled=start_disabled):
        st.session_state.trip_started = True
        st.session_state.start_gps = current_location
        st.rerun()

with col2:
    end_disabled = not st.session_state.trip_started or not current_location
    if st.button("⏹️ END TRIP", type="secondary", use_container_width=True, disabled=end_disabled):
        st.session_state.end_gps = current_location
        st.session_state.ready_to_save = True
        st.session_state.trip_started = False
        st.rerun()

# ---------------------------------------------------
# TRUCK ANIMATION - FIXED
# ---------------------------------------------------
if st.session_state.trip_started:
    st.markdown("""
    <style>
    @@keyframes truck_drive {
        0% { transform: translateX(-60px) rotate(-3deg) scale(1); }
        20% { transform: translateX(-20px) rotate(1deg) scale(1.05); }
        40% { transform: translateX(20px) rotate(0deg) scale(1.1); }
        60% { transform: translateX(50px) rotate(-1deg) scale(1.05); }
        80% { transform: translateX(20px) rotate(2deg) scale(1); }
        100% { transform: translateX(-60px) rotate(-3deg) scale(1); }
    }
    .truck-running {
        font-size: 110px !important;
        animation: truck_drive 4s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
        display: block !important;
        margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
        padding: 40px;
        border-radius: 25px;
        text-align: center;
        margin: 30px 0;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        border: 3px solid #4caf50;
    '>
        <div class='truck-running'>🚚</div>
        <h1 style='color: #2e7d32; margin: 25px 0;'>🚀 TRIP IN PROGRESS</h1>
        <div style='
            background: white;
            padding: 25px;
            border-radius: 20px;
            display: inline-block;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            max-width: 400px;
        '>
            <div style='font-size: 18px; margin-bottom: 10px;'>
                <strong>📍 From:</strong> {from_address[:70]}
            </div>
            <div style='font-size: 18px; margin-bottom: 10px;'>
                <strong>📍 To:</strong> {to_address[:70]}
            </div>
            <div style='font-size: 18px; color: #1976d2;'>
                <strong>🚗 Vehicle:</strong> {selected_vehicle}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# SAVE & SUCCESS ANIMATION
# ---------------------------------------------------
if st.session_state.ready_to_save:
    col1, col2 = st.columns(2)
    with col1:
        st.success("🎉 Trip Completed!")
        st.info(f"Route: {from_address}")
        st.info(f"Destination: {to_address}")
        st.info(f"Vehicle: {selected_vehicle}")
    
    with col2:
        if st.button("💾 SAVE TO TRACKER", type="primary", use_container_width=True):
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            map_url = f"https://www.google.com/maps/dir/{st.session_state.start_gps}/{st.session_state.end_gps}"
            
            tracker_sheet.append_row([
                end_time, selected_vehicle, from_address, to_address,
                f"{st.session_state.start_gps} → {st.session_state.end_gps}", ""
            ])
            
            last_row = len(tracker_sheet.get_all_values())
            tracker_sheet.update_acell(f"F{last_row}", f'=HYPERLINK("{map_url}","📱 Track")')
            
            # SUCCESS ANIMATION
            st.markdown("""
            <style>
            @keyframes truck_celebrate {
                0%, 100% { transform: scale(1) rotate(0deg); }
                20% { transform: scale(1.2) rotate(15deg); }
                40% { transform: scale(1.4) rotate(0deg); }
                60% { transform: scale(1.2) rotate(-15deg); }
                80% { transform: scale(1.1) rotate(5deg); }
            }
            .truck-success {
                font-size: 130px !important;
                animation: truck_celebrate 3s infinite !important;
                text-align: center !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style='
                background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
                padding: 50px;
                border-radius: 30px;
                text-align: center;
                margin: 30px 0;
                box-shadow: 0 25px 70px rgba(255,193,7,0.4);
                border: 4px solid #ff9800;
            '>
                <div class='truck-success'>🚚✨</div>
                <h1 style='color: #e65100; margin: 30px 0;'>🎊 TRIP SAVED SUCCESSFULLY!</h1>
                <p style='font-size: 22px; color: #f57c00; margin-bottom: 25px;'>✅ Recorded in Tracker Sheet</p>
                <a href='https://www.google.com/maps/dir/PLACEHOLDER' target='_blank' style='
                    display: inline-block;
                    padding: 18px 40px;
                    background: linear-gradient(45deg, #ff9800, #f57c00);
                    color: white;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: bold;
                    font-size: 20px;
                    box-shadow: 0 10px 30px rgba(255,152,0,0.4);
                    transition: all 0.3s;
                '>🗺️ View Route on Google Maps</a>
            </div>
            """, unsafe_allow_html=True)
            
            # Reset
            for key in ["trip_started", "start_gps", "end_gps", "ready_to_save"]:
                if key in st.session_state: del st.session_state[key]
            init_session_state()
            st.rerun()

# ---------------------------------------------------
# RESET & STATUS
# ---------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Reset All", type="secondary", use_container_width=True):
        for key in ["trip_started", "start_gps", "end_gps", "ready_to_save", "gps_attempts"]:
            if key in st.session_state: del st.session_state[key]
        init_session_state()
        st.rerun()

with col2:
    st.metric("GPS", "🟢 Active" if current_location else "🔴 Waiting")
    st.metric("Trip", "🟡 Running" if st.session_state.trip_started else "⚪ Ready")

st.markdown("---")
st.caption("🌐 Universal GPS | Works on PC/Mobile/Chrome/Firefox/Safari")
