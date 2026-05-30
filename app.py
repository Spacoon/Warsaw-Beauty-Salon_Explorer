import urllib.parse
import requests
import streamlit as st

# FastAPI base URL
API_URL = "http://localhost:8000/api"


def parse_rating_and_reviews(rating_str):
    """Helper to parse a rating string like '4.9 120' or '5.0 None' into float and int."""
    if not rating_str or rating_str == "None":
        return 0.0, 0
    parts = str(rating_str).split()
    try:
        r = float(parts[0])
    except (ValueError, IndexError):
        r = 0.0
    try:
        revs = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        revs = 0
    return r, revs


# Cache cleanup helper
def clear_api_caches():
    st.cache_data.clear()


# API Helpers with cache
@st.cache_data(ttl=30)
def fetch_districts():
    try:
        r = requests.get(f"{API_URL}/districts")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.sidebar.error(f"Error connecting to API (districts): {e}")
    return []


@st.cache_data(ttl=30)
def fetch_services():
    try:
        r = requests.get(f"{API_URL}/services")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.sidebar.error(f"Error connecting to API (services): {e}")
    return []


@st.cache_data(ttl=10)
def fetch_salons(district=None, service=None, search=None):
    params = {}
    if district and district != "All":
        params["district"] = district
    if service and service != "All":
        params["service"] = service
    if search:
        params["search"] = search

    try:
        r = requests.get(f"{API_URL}/salons", params=params)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Error connecting to API (salons): {e}")
    return []


def fetch_salon_details(salon_id):
    try:
        r = requests.get(f"{API_URL}/salons/{salon_id}")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Error fetching details for Salon ID {salon_id}: {e}")
    return None


# Configure the page layout
st.set_page_config(
    page_title="Warsaw Beauty Salons Directory",
    page_icon="💅",
    layout="wide"
)

# Header Section
st.title("💅 Warsaw Beauty Salons Directory")
st.markdown("Browse, search, and update details of hair and beauty salons in Warsaw.")

# Fetch all salons for statistics dashboard
all_salons = fetch_salons()
if all_salons:
    ratings = [parse_rating_and_reviews(s['rating'])[0] for s in all_salons if
               parse_rating_and_reviews(s['rating'])[0] > 0]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total Salons", len(all_salons))
    col_m2.metric("Districts Covered", len(set(s['district'] for s in all_salons)))
    col_m3.metric("Average Rating", f"{avg_rating:.2f} ⭐")

st.write("---")

# Initialize Session State
if "selected_salon_id" not in st.session_state:
    st.session_state.selected_salon_id = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

# --- SIDEBAR SEARCH AND FILTERS ---
st.sidebar.header("🔍 Filters & Sorting")

# Text search
search_query = st.sidebar.text_input(
    "Search Name or Service",
    placeholder="e.g. Manicure, Haircut...",
    value=""
)

# District Dropdown
districts = fetch_districts()
district_options = ["All"] + districts
district_filter = st.sidebar.selectbox("District", district_options)

# Service Dropdown
services = fetch_services()
service_options = ["All"] + services
service_filter = st.sidebar.selectbox("Service Type", service_options)

# Sorting Dropdown
st.sidebar.subheader("Sort Results")
sort_option = st.sidebar.selectbox(
    "Sort By",
    ["Default", "Rating (Highest first)", "Reviews (Most first)", "Name (A-Z)"]
)

# Clear Filter button
if st.sidebar.button("Clear All Filters"):
    st.sidebar.info("Filters cleared.")
    st.rerun()

# Fetch filtered list of salons
salons = fetch_salons(
    district=district_filter,
    service=service_filter,
    search=search_query
)

# Apply Sorting
if sort_option == "Rating (Highest first)":
    salons.sort(key=lambda s: parse_rating_and_reviews(s['rating'])[0], reverse=True)
elif sort_option == "Reviews (Most first)":
    salons.sort(key=lambda s: parse_rating_and_reviews(s['rating'])[1], reverse=True)
elif sort_option == "Name (A-Z)":
    salons.sort(key=lambda s: s['name'].lower())

# --- MAIN PAGE LAYOUT ---
# Left column for listing, right column for details & edit
col_list, col_details = st.columns([1.2, 1.8])

# --- LEFT COLUMN: SALON LISTING ---
with col_list:
    st.subheader(f"Salons Found ({len(salons)})")

    if not salons:
        st.info("No salons found matching your filters. Try adjusting your search query.")
    else:
        # Loop through and display basic info for each salon in a clean card container
        for s in salons:
            with st.container(border=True):
                # Check for top-rated status to add a visual badge
                r_val, r_count = parse_rating_and_reviews(s['rating'])
                badge_str = " 🏆" if (r_val >= 4.9 and r_count >= 50) else ""
                st.markdown(f"### {s['name']}{badge_str}")
                st.write(f"📍 **District:** {s['district']}")

                # Format ratings nicely
                rating_raw = s['rating']
                rating_display = "⭐ None"
                if rating_raw and rating_raw != "None":
                    parts = rating_raw.split()
                    try:
                        val = float(parts[0])
                        val_str = f"{val:.2f}"
                    except ValueError:
                        val_str = parts[0]
                    if len(parts) >= 2:
                        rating_display = f"⭐ {val_str} ({parts[1]} reviews)"
                    elif len(parts) == 1:
                        rating_display = f"⭐ {val_str}"

                st.write(f"✨ **Rating:** {rating_display}")
                price = s['price_range'] if s['price_range'] else "N/A"
                st.write(f"💰 **Price Range:** {price}")

                # Check if this salon is currently selected to highlight/style differently
                is_selected = st.session_state.selected_salon_id == s['id']
                btn_label = "👉 Selected" if is_selected else "👁️ View Details"

                if st.button(btn_label, key=f"sel_{s['id']}", use_container_width=True,
                             type="secondary" if not is_selected else "primary"):
                    st.session_state.selected_salon_id = s['id']
                    st.session_state.edit_mode = False
                    st.rerun()

# --- RIGHT COLUMN: DETAILS AND EDITING ---
with col_details:
    selected_id = st.session_state.selected_salon_id

    if selected_id is None:
        st.subheader("Salon Details")
        st.info("👈 Select a salon from the list on the left to see its full details and make edits.")
    else:
        # Fetch full details
        details = fetch_salon_details(selected_id)

        if not details:
            st.error("Failed to load salon details from API.")
        else:
            if not st.session_state.edit_mode:
                # --- DISPLAY MODE ---
                # Highlight top-rated status
                r_val, r_count = parse_rating_and_reviews(details['rating'])
                is_top_rated = r_val >= 4.9 and r_count >= 50

                title_suffix = " 🏆 (Top Rated)" if is_top_rated else ""
                st.subheader(f"{details['name']}{title_suffix}")

                # Google Maps Link using Name & City
                quoted_name = urllib.parse.quote(f"{details['name']}, Warszawa")
                maps_url = f"https://www.google.com/maps/search/?api=1&query={quoted_name}"
                st.markdown(f"📍 **Address:** [{details['address']}]({maps_url})")

                st.write(f"🏙️ **District:** {details['district']}")

                # Phone Number display (only if present)
                if details.get('phone') and details['phone'].strip():
                    st.write(f"📞 **Phone Number:** {details['phone']}")

                # Rating formatting
                rating_raw = details['rating']
                rating_display = "⭐ None"
                if rating_raw and rating_raw != "None":
                    parts = rating_raw.split()
                    try:
                        val = float(parts[0])
                        val_str = f"{val:.2f}"
                    except ValueError:
                        val_str = parts[0]
                    if len(parts) >= 2:
                        rating_display = f"⭐ {val_str} ({parts[1]} reviews)"
                    elif len(parts) == 1:
                        rating_display = f"⭐ {val_str}"
                st.write(f"✨ **Rating:** {rating_display}")

                price = details['price_range'] if details['price_range'] else "N/A"
                st.write(f"💰 **Price Range:** {price} PLN")

                st.write("**🌐 Website / Social Links:**")
                if details['websites']:
                    for site in details['websites']:
                        st.markdown(f"- [{site}]({site})")
                else:
                    st.write("*No websites or social links available*")

                st.write("**💇‍♀️ Services Offered:**")
                if details['services']:
                    # Build custom HTML badges using standard streamlit markdown helper
                    badges = "".join([
                        f'<span style="background-color:#E2E8F0; color:#1A202C; padding:3px 8px; margin:2px; border-radius:12px; display:inline-block; font-size:12px; font-weight:500;">{service}</span>'
                        for service in details['services']
                    ])
                    st.markdown(badges, unsafe_allow_html=True)
                else:
                    st.write("*No services registered*")

                st.write("---")

                # Edit Button
                if st.button("✏️ Edit Salon Details", use_container_width=True):
                    st.session_state.edit_mode = True
                    st.rerun()

            else:
                # --- EDIT MODE ---
                st.subheader(f"✏️ Edit Salon: {details['name']}")

                with st.form("edit_salon_form"):
                    name = st.text_input("Business Name", value=details['name'])
                    address = st.text_input("Address", value=details['address'])

                    # District Selection (populated from API)
                    districts_list = fetch_districts()
                    if details['district'] not in districts_list:
                        districts_list = [details['district']] + districts_list
                    try:
                        dist_idx = districts_list.index(details['district'])
                    except ValueError:
                        dist_idx = 0
                    district = st.selectbox("District", districts_list, index=dist_idx)

                    # Phone Number Input (manual input enabled)
                    phone = st.text_input("Phone Number", value=details.get('phone', ''),
                                          help="Enter phone number (optional, e.g. +48 123 456 789)")

                    price_range = st.text_input("Price Range (PLN)", value=details['price_range'],
                                                help="e.g. 50.00 - 300.00")
                    rating = st.text_input("Rating & Review Count String", value=details['rating'],
                                           help="e.g. 4.9 220")

                    # Websites multi-line editor
                    websites_raw = "\n".join(details['websites'])
                    websites_text = st.text_area(
                        "Website & Social Media Links (one link per line)",
                        value=websites_raw,
                        help="Enter website URLs, each on a new line."
                    )

                    # Services multi-line editor
                    services_raw = "\n".join(details['services'])
                    services_text = st.text_area(
                        "Services Offered (one service per line)",
                        value=services_raw,
                        help="Enter names of services, each on a new line."
                    )

                    # Save / Cancel Buttons in form
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                    with col_cancel:
                        cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

                # Check for button events (must check outside the columns/form context for standard streamlit form submission layout)
                if save_btn:
                    if not name.strip() or not address.strip() or not district.strip():
                        st.error("Name, Address, and District are required.")
                    else:
                        # Process multi-line text boxes back into arrays
                        new_websites = [line.strip() for line in websites_text.split("\n") if line.strip()]
                        new_services = [line.strip() for line in services_text.split("\n") if line.strip()]

                        payload = {
                            "name": name.strip(),
                            "address": address.strip(),
                            "district": district.strip(),
                            "phone": phone.strip(),
                            "websites": new_websites,
                            "services": new_services,
                            "price_range": price_range.strip(),
                            "rating": rating.strip()
                        }

                        # PUT request to API to update
                        try:
                            res = requests.put(f"{API_URL}/salons/{selected_id}", json=payload)
                            if res.status_code == 200:
                                st.toast("🎉 Changes saved successfully!", icon="✅")
                                st.session_state.edit_mode = False
                                clear_api_caches()
                                st.rerun()
                            else:
                                st.error(f"Failed to update salon: {res.text}")
                        except Exception as e:
                            st.error(f"Error sending update request: {e}")

                if cancel_btn:
                    st.session_state.edit_mode = False
                    st.rerun()
