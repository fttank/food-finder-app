import requests
import random
import datetime
import streamlit as st
import folium
from streamlit_folium import st_folium

# Page Configuration (Must be the first Streamlit command)
st.set_page_config(
    page_title="The 'IDK' Dinner Solution",
    page_icon="🍔"
)

# Custom CSS
st.markdown("""
    <style>
    /* Keyframes for the slide-in animation */
    @keyframes slideInUp {
        0% { 
        transform: translateY(20px); 
        }
        100% { 
        transform: translateY(0); 
        }
    }
    /* Class to apply the animation and hover transition to result cards */
    .results-card {
        animation: none;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        background-color: #3D5A80; 
        border: 1px solid #98C1D9;
        border-radius: 10px;
        padding: 15px; 
        margin-bottom: 15px; 
        display: flex; 
        align-items: center;
    }
    .results-card:hover {
        transform: scale(1.02);
        animation: slideInUp 0.2s ease-out forwards;
    }
    /* Set the main background color */
    [data-testid="stAppViewContainer"] > .main {
        background-color: #293241;
    }
    /* Style for the custom labels in the form */
    p.input-label {
        text-align: center;
        font-size: 16px;
        color: #98C1D9;
        margin: 0;
        padding-bottom: 5px;
    }
    /* Style for the text INSIDE the input boxes */
    div[data-testid="stTextInput"] input {
        font-size: 16px;
        color: #E0FBFC;
        text-align: center;
    }
    /* Style for the main button */
    div[data-testid="stForm"] button {
        background-color: #EE6C4D;
        color: #E0FBFC;
        border-radius: 10px;
        border: none;
        padding: 10px 20px;
        width: 100%;
    }
    /* Style for the button on hover */
    div[data-testid="stForm"] button:hover {
        background-color: #E0FBFC;
        color: #293241;
        cursor: pointer;
    }
    /* Style to center the submit button */
    div[data-testid="stFormSubmitButton"] {
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)


# Helper Functions

# Gets the simple 'Open Now' or 'Closed Now' status from the initial search results
def get_closing_time_status(business):

    now = datetime.datetime.now()
    today_weekday = now.weekday()

    # Get detailed hours data, which was fetched and added previously.
    hours_info = business.get('detailed_hours_data')

    # Use the 'is_open_now' flag from the detailed API response as the most reliable indicator.
    if not hours_info or not isinstance(hours_info, list) or not hours_info[0].get('is_open_now'):
        return '<span style="color: #EE6C4D;">Closed Now</span>'

    # If Yelp says it's open, find the closing time for the current operational window.
    open_periods = hours_info[0].get('open', [])

    # Check for an overnight period from yesterday that we might be in.
    yesterday_weekday = (today_weekday - 1 + 7) % 7
    for period in open_periods:
        if period.get('day') == yesterday_weekday and period.get('is_overnight'):
            end_time = datetime.datetime.strptime(period.get('end'), '%H%M').time()
            if now.time() < end_time:
                closing_time_formatted = end_time.strftime('%I:%M %p').strip()
                return f'<span style="color: #80ED99;">Open Until: {closing_time_formatted}</span>'

    # Check for regular periods today.
    for period in open_periods:
        if period.get('day') == today_weekday:
            start_time = datetime.datetime.strptime(period.get('start'), '%H%M').time()
            end_time = datetime.datetime.strptime(period.get('end'), '%H%M').time()

            # For normal, non-overnight shifts today
            if not period.get('is_overnight') and start_time <= now.time() < end_time:
                closing_time_formatted = end_time.strftime('%I:%M %p').strip()
                return f'<span style="color: #80ED99;">Open Until: {closing_time_formatted}</span>'

            # For shifts that start today and run overnight
            if period.get('is_overnight') and start_time <= now.time():
                closing_time_formatted = end_time.strftime('%I:%M %p').strip()
                return f'<span style="color: #80ED99;">Open Until: {closing_time_formatted}</span>'
    # Fallback if 'is_open_now' is true but no matching time block was found.
    return '<span style="color: #80ED99;">Open</span>'

# Calls the Yelp Search API and returns the JSON response
def search_yelp(api_key, term, location):
    endpoint = 'https://api.yelp.com/v3/businesses/search'
    headers = {'Authorization': f'Bearer {api_key}'}
    params = {'term': term, 'location': location, 'categories': 'restaurants', 'with_hours': 'true'}
    try:
        response = requests.get(url=endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

# Calls the Yelp Business Details API for a single business.
def get_business_details(api_key, business_id):
    endpoint = f'https://api.yelp.com/v3/businesses/{business_id}'
    headers = {'Authorization': f'Bearer {api_key}'}
    try:
        response = requests.get(url=endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

# Checks for potentially dangerous characters in user input
def is_input_safe(user_input):
    forbidden_chars = {'<', '>', '\"', '\'', '{', '}', '&'}
    for char in user_input:
        if char in forbidden_chars:
            return False
    return True

# Displays the map and the list of restaurants in Streamlit.
def display_results(data):
    if not data or not data.get('businesses'):
        st.warning("Interesting... that doesn't seem to exist yet...Let's try that again.")
        return

    businesses = sorted(data['businesses'], key=lambda b: b['rating'], reverse=True)
    lats = [b['coordinates']['latitude'] for b in businesses if b.get('coordinates')]
    lons = [b['coordinates']['longitude'] for b in businesses if b.get('coordinates')]
    if lats:
        map_center = [sum(lats) / len(lats), sum(lons) / len(lons)]
        m = folium.Map(location=map_center, zoom_start=12, tiles="CartoDB positron")
        for i, business in enumerate(businesses):
            coords = business.get('coordinates')
            if coords:
                name = business.get('name', 'N/A')
                folium.Marker(location=[coords['latitude'], coords['longitude']], tooltip=f"#{i + 1}: {name}").add_to(m)
        st_folium(m, width=700, height=450)

    for i, business in enumerate(businesses):
        if not business.get('is_closed'):
            name, rating, price = business.get('name', 'N/A'), business.get('rating', 'N/A'), business.get('price', 'N/A')
            address = business.get('location', {}).get('display_address', ['N/A'])[0]
            url, image_url = business.get('url', '#'), business.get('image_url')
            business_id = business.get('id')
            status = get_closing_time_status(business)

            # Tile animation delay
            delay = i * 0.1

            st.markdown(f"""
            <a href="{url}" target="_blank" style="text-decoration: none;">
                <div class="results-card">
                    <img src="{image_url}" style="width: 120px; height: 120px; border-radius: 8px; margin-right: 20px; object-fit: cover;">
                    <div>
                        <h5 style="margin: 0; font-weight: bold; color: #EE6C4D; font-size: 20px;">{i + 1}. {name} ({rating} ★) {price}</h5>
                        <p style="margin: 8px 0 0 0; font-size: 16px; color: #98C1D9;">{address}</p>
                        <p style="margin: 5px 0 0 0; font-size: 16px; color: #98C1D9;">Status: {status}</p>
                    </div>
                </div>
            </a>
            """, unsafe_allow_html=True)

# Main App Interface
st.markdown("""
    <div style="background-color: #3D5A80; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
        <h1 style="text-shadow: 2px 2px 4px rgba(0,0,0,0.2); text-align: center; font-weight: bold; 
            font-size: 60px; text-transform: uppercase; color: #E0FBFC; margin: 0;">Let's Eat Whatever!</h1>
    </div>
""", unsafe_allow_html=True)

# Control Panel
with st.container():
    st.markdown(
        "<h3 style='text-align: center; color: #E0FBFC;'>Tired of the endless 'what do you want to eat?' debate?</h3>",
        unsafe_allow_html=True)
    st.markdown("<h5 style='text-align: center; color: #98C1D9;'>Start solving dinner arguments since right now!</h5>",
                unsafe_allow_html=True)
    status_placeholder = st.empty()
    with st.form("search_form"):
        left_col, mid_col, right_col = st.columns([1, 2, 1])
        with mid_col:
            st.markdown("<p class='input-label'>Okay, but what are you secretly craving? (Optional)</p>",
                        unsafe_allow_html=True)
            search_term = st.text_input("Search Term", label_visibility="collapsed")
            st.markdown("<p class='input-label'>What's your zip code or neighborhood?</p>", unsafe_allow_html=True)
            location = st.text_input("Location", label_visibility="collapsed")
            submitted = st.form_submit_button("Oracle Choose For Me!")
# Once User hits submit
if submitted:
    status_placeholder.empty()
    if 'last_search_result' in st.session_state: del st.session_state['last_search_result']
    if 'random_choice_message' in st.session_state: del st.session_state['random_choice_message']

    if not is_input_safe(search_term) or not is_input_safe(location):
        status_placeholder.error("Invalid characters detected. Please use only letters and numbers.")
    elif not location:
        status_placeholder.warning("Please enter a zip code or neighborhood!")
    else:
        is_random_choice = not search_term
        clean_search = search_term.split(' ')[0]
        if is_random_choice:
            food_options = ['Pizza 🍕', 'Burgers 🍔', 'Tacos 🌮', 'Sandwiches 🥪', 'Sushi 🍣', 'BBQ 🍖']
            random_choice = random.choice(food_options)
            clean_search = random_choice.split(' ')[0]

        with st.spinner("Consulting the Yelp Spirits..."):
            try:
                api_key = st.secrets["YELP_API_KEY"]
                yelp_data = search_yelp(api_key, clean_search, location)

                # This loop saves the details to each business
                if yelp_data and yelp_data.get("businesses"):
                    businesses = yelp_data.get('businesses', [])
                    for business in businesses:
                        details = get_business_details(api_key, business['id'])
                        if details:
                            business['detailed_hours_data'] = details.get('hours')
                        else:
                            business['detailed_hours_data'] = None
                    # Save the enriched data to the session state after the loop is done
                    st.session_state['last_search_result'] = yelp_data
                    if is_random_choice and yelp_data.get("businesses"):
                        st.session_state['random_choice_message'] = f"""
                            <p style="text-align: center; text-transform: uppercase; font-weight: bold; 
                            font-size: 20px; color: #EE6C4D; text-decoration: underline;">The Oracle has Chosen: {random_choice}</p>"""
                else:
                    status_placeholder.error("That location seems to be invalid.")

            except KeyError:
                status_placeholder.error("YELP_API_KEY not found in secrets.toml. Please check your configuration.")
                st.stop()

# Display Logic (Runs on every reload)
if 'random_choice_message' in st.session_state:
    st.markdown(st.session_state['random_choice_message'], unsafe_allow_html=True)

if 'last_search_result' in st.session_state:
    display_results(st.session_state['last_search_result'])
