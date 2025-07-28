import requests, random, json, datetime
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Page Config
st.set_page_config(
    page_title="The 'IDK' Dinner Solution",
    page_icon="🍔"
)

# --- Custom CSS to make text input bigger ---
st.markdown("""
    <style>
    /* Style for the custom labels in the sidebar */
    p.input-label {
        text-align: center;
        font-size: 16px;
        color: #C7F9CC;
        margin: 0;
    }
    
    /* Style for the text INSIDE the input boxes */
    div[data-testid="stTextInput"] input {
        font-size: 16px;
        color: #38A3A5;
    }
   
    /* Style for the main button */
    div[data-testid="stForm"] button {
        background-color: #191716;
        color: #C7F9CC;
        border-radius: 10px;
        border: none;
        padding: 10px 10px;
    }
    
    /* Style for the button on hover */
    div[data-testid="stForm"] button:hover {
        background-color: #80ED99;
        color: #191716;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper Functions
# Formats Yelp's hours data into a readable string for today
def format_hours(hours_data, current_day_index):
    if not hours_data or not hours_data[0].get('open'):
        return "Hours not available"

    for day_info in hours_data[0]['open']:
        if day_info['day'] == current_day_index:
            try:
                start_time_obj = datetime.datetime.strptime(day_info['start'], '%H%M')
                end_time_obj = datetime.datetime.strptime(day_info['end'], '%H%M')
                end_time_12hr = end_time_obj.strftime('%I:%M %p').strip()
                return f"{end_time_12hr}"
            except:
                return "Hours unavailable"
    return "Closed today"

# Calls the Yelp API and returns the JSON response.
def search_yelp(api_key, term, location):
    endpoint = 'https://api.yelp.com/v3/businesses/search'
    headers = {'Authorization': f'Bearer {api_key}'}
    params = {'term': term, 'location': location, 'categories': 'restaurants'}

    try:
        response = requests.get(url=endpoint, headers=headers, params=params)
        response.raise_for_status() # This will handle 4xx/5xx errors
        return response.json()
    except requests.exceptions.RequestException:
        st.error(f"Lets try that zip code one more time. Try again!")
        return None

#  Displays the map and the list of restaurants in Streamlit.
def display_results(data):
    # In case user's input does not have a result
    if not data or not data.get('businesses'):
        st.warning("That's an amazing craving but... it doesn't seem to exist yet...Let's try that again.")
        return

    # Grabbing business information and sorting it by rating
    businesses = data['businesses']
    business_sorted = sorted(businesses, key=lambda b: b['rating'], reverse=True)
    today_index = datetime.datetime.now().weekday() # displays businesses operating hours for the day

    # Folium Map Logic
    lats = [b['coordinates']['latitude'] for b in business_sorted if b.get('coordinates')]
    lons = [b['coordinates']['longitude'] for b in business_sorted if b.get('coordinates')]

    if lats:
        map_center = [sum(lats) / len(lats), sum(lons) / len(lons)]
        m = folium.Map(location=map_center, zoom_start=12)

        for i, business in enumerate(business_sorted):  # Use enumerate to get the rank (i)
            coords = business.get('coordinates')
            if coords:
                name = business.get('name', 'N/A')
                folium.Marker(
                    location=[coords['latitude'],coords['longitude']],
                    tooltip=f"#{i + 1}:{name}"
                ).add_to(m)

        with st.spinner('Loading up the map...'):
            st_folium(m, width=700, height=450)

    # Results List Logic
    for i, business in enumerate(business_sorted):
        # Skips all non-operating businesses and displays all available business information
        if not business.get('is_closed'):
            name = business.get('name', 'N/A')
            url = business.get('url', '#')
            img_url = business.get('image_url')
            rating = business.get('rating', 'N/A')
            price = business.get('price', 'N/A')
            hours = format_hours(business.get('business_hours', []), today_index)
            address = business.get('location', {}).get('display_address', ['N/A'])[0]

            # HTML formatting for displaying results with business image
            st.markdown(f"""
            <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">
                <div style="
                    background-color: #191716;
                    border: 1px solid #2A4849;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
                ">
                    <img src="{img_url}" style="
                        width: 120px;
                        height: 120px;
                        border-radius: 8px;
                        margin-right: 20px;
                        object-fit: cover;
                    ">
                    <div>
                        <h5 style="margin: 0; font-weight: bold; color: #80ED99; font-size: 24px; text-decoration: underline;">{i + 1}. {name} ({rating} ★) {price}</h5>
                        <p style="margin: 5px 0 0 0; font-size: 18px; color: #38A3A5;">{address}</p>
                        <p style="margin: 5px 0 0 0; font-size: 18px; color: #38A3A5;">Open until: {hours}</p>
                    </div>
                </div>
            </a>
            """, unsafe_allow_html=True)

# Headers for main page, HTML
st.markdown("""
    <div style = "
        background-color: #191716;
        border: 1px solid #2A4849;
        border-radius: 10px;
        padding: 5px;
        margin-bottom: 1px;
        display: flex;
        align-items: center;
    ">
        <h1 style="
            text-shadow: 2px 2px 4px rgba(0,0,0.5,0.5);
            text-align: center; 
            font-weight: bold; 
            font-size: 60px; 
            text-transform: uppercase;
            color: #C7F9CC;
            margin: 0px auto;
            ">
                Let's Eat Whatever!
        </h1>
    </div>
""", unsafe_allow_html=True)

# Sidebar controls
st.sidebar.markdown("""
    <div style = "
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    ">
        <h1 style="text-align: center; font-size: 30px; font-weight: bold; color: #80ED99;">Tired of the endless <br>'what do you want to eat?' <br>debate?</h1>
        <h3 style="text-align: center; color: #38A3A5;">Start solving dinner arguments since right now!</h3>
    </div>
""", unsafe_allow_html=True)

with st.sidebar.form("search_form"):
    # Adding style to labels
    st.markdown("<p class='input-label'>Okay, but what are you secretly craving? (Optional)</p>", unsafe_allow_html=True)
    search_term = st.text_input("Search Term", label_visibility="collapsed")

    st.markdown("<p class='input-label'>What's your zip code or neighborhood?</p>", unsafe_allow_html=True)
    location = st.text_input("Location", label_visibility="collapsed")

    left_col, mid_col, right_col = st.columns([5, 6, 5])
    with mid_col:
        submitted = st.form_submit_button("Oracle Choose For Me!")

    # This block only performs actions when the form is submitted.
    if submitted:
        # Clear the old search results first
        if 'last_search_result' in st.session_state:
            del st.session_state['last_search_result']
        if 'random_choice_message' in st.session_state:
            del st.session_state['random_choice_message']

       # First, check if a location was provided.
        if not location:
            st.warning("Please enter a zip code or neighborhood!")
        else:
            # If location is valid, then proceed with the search logic.
            clean_search = search_term
            if not search_term:
                food_options = [
                    'Pizza 🍕', 'Burgers 🍔', 'Tacos 🌮', 'Sandwiches 🥪', 'Sushi 🍣', 'BBQ 🍖',
                    'Thai 🍛', 'Chinese 🥡', 'Ramen 🍜', 'Pho 🍲', 'Korean 🥢', 'Indian 🌶️',
                    'Italian 🍝', 'Mediterranean 🥗', 'Greek 🥙', 'French 🥐',
                    'Seafood 🦞', 'Steakhouse 🥩', 'Vegan 🌱', 'Vegetarian', 'Breakfast 🥞'
                ]
                random_choice = random.choice(food_options)
                st.session_state['random_choice_message'] = f"""
                <p style="
                    text-align: center;
                    text-transform: uppercase; 
                    font-weight: bold; font-size: 20px; 
                    color: #C7F9CC;
                    text-decoration: underline;
                    ">
                        The Oracle has Chosen: {random_choice}
                    </p>
                """
                clean_search = random_choice.split(' ')[0]
            else:
                # Clear any old random choice message if the user typed something
                if 'random_choice_message' in st.session_state:
                    del st.session_state['random_choice_message']

            with st.spinner("Consulting the Yelp Spirits..."):
                try:
                    api_key = st.secrets["YELP_API_KEY"]
                    # Calling search function with inputs from text boxes
                    yelp_data = search_yelp(api_key, clean_search, location)
                    st.session_state['last_search_result'] = yelp_data
                except KeyError:
                    st.error("Please enter a zip code or neighborhood!")

# This part runs EVERY time and displays whatever is currently in the app's memory.
if 'random_choice_message' in st.session_state:
    st.markdown(st.session_state['random_choice_message'], unsafe_allow_html=True)

if 'last_search_result' in st.session_state:
    display_results(st.session_state['last_search_result'])