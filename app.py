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

    spreadsheet = client.open_by_key(
        "1Cwe5jN7iiNYV9LKReshFl_BLvcuAJ3pgMeWBWaRstCY"
    )

    return (
        spreadsheet.worksheet("Cus_Details"),
        spreadsheet.worksheet("Tracker")
    )

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

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "trip_started" not in st.session_state:
    st.session_state.trip_started = False

if "ready_to_save" not in st.session_state:
    st.session_state.ready_to_save = False

if "start_gps" not in st.session_state:
    st.session_state.start_gps = ""

if "end_gps" not in st.session_state:
    st.session_state.end_gps = ""

if "start_lat" not in st.session_state:
    st.session_state.start_lat = ""

if "start_lng" not in st.session_state:
    st.session_state.start_lng = ""

if "end_lat" not in st.session_state:
    st.session_state.end_lat = ""

if "end_lng" not in st.session_state:
    st.session_state.end_lng = ""

# ---------------------------------------------------
# LOCATION SECTION
# ---------------------------------------------------
col1, col2 = st.columns(2)

with col1:

    location_names = ["Office"] + customer_df[
        "Name"
    ].dropna().tolist()

    from_location = st.selectbox(
        "From",
        location_names
    )

    to_location = st.selectbox(
        "To",
        customer_df["Name"].dropna().tolist()
    )

with col2:

    from_address = "Office"

    if from_location != "Office":

        from_row = customer_df[
            customer_df["Name"] == from_location
        ].iloc[0]

        from_address = from_row["address"]

    to_row = customer_df[
        customer_df["Name"] == to_location
    ].iloc[0]

    to_address = to_row["address"]

    st.text_input(
        "From Address",
        value=from_address,
        disabled=True
    )

    st.text_input(
        "To Address",
        value=to_address,
        disabled=True
    )

# ---------------------------------------------------
# VEHICLE
# ---------------------------------------------------
vehicle_numbers = sorted(
    customer_df["delivery_vh_no"]
    .dropna()
    .unique()
    .tolist()
)

selected_vehicle = st.selectbox(
    "Vehicle Number",
    vehicle_numbers
)

# ---------------------------------------------------
# LIVE GPS TRACKING
# ---------------------------------------------------
st.markdown("---")

st.subheader("📱 Live GPS Tracking")

gps_data = streamlit_js_eval(
    js_expressions="""
    new Promise((resolve) => {

        if (!navigator.geolocation) {
            resolve(null);
            return;
        }

        navigator.geolocation.watchPosition(

            (position) => {

                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: position.timestamp
                });

            },

            (error) => {
                resolve(null);
            },

            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    });
    """,
    key="live_gps_tracking"
)

current_location = ""

if gps_data:

    current_lat = gps_data["latitude"]

    current_lng = gps_data["longitude"]

    accuracy = gps_data["accuracy"]

    current_location = (
        f"{current_lat},{current_lng}"
    )

    st.success("✅ Live GPS Connected")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Latitude",
            f"{current_lat:.6f}"
        )

    with c2:
        st.metric(
            "Longitude",
            f"{current_lng:.6f}"
        )

    with c3:
        st.metric(
            "Accuracy",
            f"{accuracy:.1f} m"
        )

else:

    st.error("❌ Waiting For GPS Access")

# ---------------------------------------------------
# CONTROL BUTTONS
# ---------------------------------------------------
st.markdown("---")

col1, col2 = st.columns(2)

# ---------------------------------------------------
# START BUTTON
# ---------------------------------------------------
with col1:

    if st.button(
        "🚀 START TRIP",
        use_container_width=True
    ):

        if current_location != "":

            st.session_state.trip_started = True

            st.session_state.start_lat = current_lat

            st.session_state.start_lng = current_lng

            st.session_state.start_gps = (
                f"{current_lat},{current_lng}"
            )

            st.success("✅ Travel Started")

            st.rerun()

        else:

            st.error("GPS Required")

# ---------------------------------------------------
# END BUTTON
# ---------------------------------------------------
with col2:

    if st.button(
        "⏹️ END TRIP",
        use_container_width=True
    ):

        if st.session_state.trip_started:

            st.session_state.end_lat = current_lat

            st.session_state.end_lng = current_lng

            st.session_state.end_gps = (
                f"{current_lat},{current_lng}"
            )

            st.session_state.trip_started = False

            st.session_state.ready_to_save = True

            st.success(
                f"✅ You traveled from "
                f"{from_address} to {to_address}"
            )

            st.rerun()

        else:

            st.warning("Start trip first")

# ---------------------------------------------------
# RUNNING ANIMATION
# ---------------------------------------------------
if st.session_state.trip_started:

    st.markdown("""
    <div style='text-align:center;
                padding:30px;'>

        <div style='font-size:100px;
                    animation: drive 1s infinite alternate;'>
            🚚
        </div>

        <h2>Trip In Progress</h2>

    </div>

    <style>
    @keyframes drive {
        from {
            transform: translateX(-40px);
        }
        to {
            transform: translateX(40px);
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# SAVE SECTION
# ---------------------------------------------------
if st.session_state.ready_to_save:

    st.markdown("---")

    st.subheader("💾 Save Trip")

    st.info(f"From: {from_address}")

    st.info(f"To: {to_address}")

    st.info(f"Vehicle: {selected_vehicle}")

    if st.button(
        "✅ SAVE TO TRACKER",
        use_container_width=True
    ):

        try:

            end_time = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # ---------------------------------------------------
            # GOOGLE MAP ROUTE
            # ---------------------------------------------------
            map_url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin="
                f"{st.session_state.start_lat},"
                f"{st.session_state.start_lng}"
                f"&destination="
                f"{st.session_state.end_lat},"
                f"{st.session_state.end_lng}"
                f"&travelmode=driving"
            )

            # ---------------------------------------------------
            # SAVE TO SHEET
            # ---------------------------------------------------
            tracker_sheet.append_row([

                end_time,

                selected_vehicle,

                from_address,

                to_address,

                (
                    f"{st.session_state.start_gps}"
                    f" → "
                    f"{st.session_state.end_gps}"
                ),

                ""
            ])

            # ---------------------------------------------------
            # TRACK LINK
            # ---------------------------------------------------
            last_row = len(
                tracker_sheet.get_all_values()
            )

            tracker_sheet.update_acell(
                f"F{last_row}",
                f'=HYPERLINK("{map_url}","Track")'
            )

            st.success(
                "✅ Trip Saved Successfully"
            )

            # ---------------------------------------------------
            # RESET
            # ---------------------------------------------------
            st.session_state.trip_started = False

            st.session_state.ready_to_save = False

            st.session_state.start_gps = ""

            st.session_state.end_gps = ""

            st.rerun()

        except Exception as e:

            st.error(str(e))

# ---------------------------------------------------
# STATUS
# ---------------------------------------------------
st.markdown("---")

gps_status = (
    "🟢 Active"
    if current_location
    else "🔴 Disabled"
)

trip_status = (
    "🟡 Running"
    if st.session_state.trip_started
    else "⚪ Idle"
)

c1, c2 = st.columns(2)

with c1:
    st.metric("GPS Status", gps_status)

with c2:
    st.metric("Trip Status", trip_status)
