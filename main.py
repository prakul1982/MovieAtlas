# main.py

import streamlit as st
import requests
import random
import html
from typing import Dict, List, Tuple, Any, Optional

# --- Page Configuration (MUST be the first Streamlit command) ---
st.set_page_config(
    layout="wide",
    page_title="MovieAtlas",
    page_icon="🍿"
)

# --- Constants ---
NUM_COLUMNS = 5
MIN_YEAR = 1900
MAX_YEAR = 2025
DEFAULT_YEAR_RANGE = (2000, 2025)
DEFAULT_MIN_RATING = 6.0
MAX_API_PAGES = 500

# --- Supported Languages for Filtering ---
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Malayalam": "ml",
}
LANGUAGE_OPTIONS = ["Any"] + sorted(list(SUPPORTED_LANGUAGES.keys()))


# --- Import Local Modules & Configuration ---
try:
    from config import API_KEY, BASE_URL, IMAGE_BASE_URL
    from api_utils import load_genres, search_person, fetch_movies, fetch_movie_details
    from utils import display_movie_details, previous_page, next_page, format_rating
except ImportError as e:
    st.error(f"Fatal Error: Could not import required modules (config/api_utils/utils). Please ensure they exist. Details: {e}")
    st.stop()

# --- Early Exit if API Key is Missing/Invalid ---
if not API_KEY or "YOUR_ACTUAL_TMDB_API_V4_BEARER_TOKEN" in API_KEY:
    st.error("TMDB API Key (v4 Bearer Token) is missing or invalid in `config.py`. Please add your key.")
    st.info("You can get a key from [The Movie Database (TMDB)](https://www.themoviedb.org/settings/api). Make sure to use the 'API Read Access Token (v4 auth)'")
    st.stop()
if not BASE_URL or not IMAGE_BASE_URL:
     st.error("Base URLs (BASE_URL, IMAGE_BASE_URL) missing in `config.py`.")
     st.stop()


# --- Load Genres ---
@st.cache_data
def get_genres() -> Dict[int, str]:
    genres_dict = load_genres()
    if not genres_dict:
        st.warning("Could not load movie genres from TMDB. Genre filtering disabled.", icon="⚠️")
    return genres_dict

GENRES = get_genres()
GENRE_OPTIONS = ["All"] + sorted(list(GENRES.values())) if GENRES else ["All"]

# --- Mood to Genre Mapping ---
MOOD_TO_GENRE_IDS = {}
if GENRES:
    REVERSE_GENRES = {name: id for id, name in GENRES.items()}
    MOOD_TO_GENRE_IDS = {
        "Exciting": [REVERSE_GENRES.get(g) for g in ["Action", "Adventure", "Thriller", "Science Fiction"] if g in REVERSE_GENRES],
        "Romantic": [REVERSE_GENRES.get(g) for g in ["Romance", "Comedy"] if g in REVERSE_GENRES],
        "Thought-provoking": [REVERSE_GENRES.get(g) for g in ["Drama", "Mystery", "Science Fiction"] if g in REVERSE_GENRES],
        "Funny": [REVERSE_GENRES.get(g) for g in ["Comedy"] if g in REVERSE_GENRES],
        "Action-packed": [REVERSE_GENRES.get(g) for g in ["Action", "Adventure", "Science Fiction"] if g in REVERSE_GENRES],
        "Suspenseful": [REVERSE_GENRES.get(g) for g in ["Thriller", "Horror", "Mystery"] if g in REVERSE_GENRES],
    }
    MOOD_TO_GENRE_IDS = {mood: [id for id in ids if id is not None] for mood, ids in MOOD_TO_GENRE_IDS.items()}

MOOD_OPTIONS = ["All"] + sorted(list(MOOD_TO_GENRE_IDS.keys()))

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes required keys in Streamlit's session state."""
    defaults = {
        'page': 1,
        'selected_movie_id': None,
        'actor_id_result': None,
        'director_id_result': None,
        'searched_actor_name': None,
        'searched_director_name': None,
        'surprise_mode': False,
        'surprise_just_shown': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Styling ---
def apply_custom_css():
    """Applies custom CSS styling to the app."""
    css = """
        <style>
            /* General */
            .stApp { background-color: #1E1E1E; color: #EAEAEA; animation: fade-in 0.5s ease-in-out forwards; }
            @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
            h1 { color: #FFFFFF; text-align: center; margin-bottom: 2rem; font-weight: 600; }
            h2, h3 { color: #DDDDDD; text-align: center; margin-bottom: 1rem; }
            a { color: #1E90FF; text-decoration: none; } a:hover { color: #46aaff; }
            p, li { color: #EAEAEA; } strong { color: #FFFFFF; }
            hr { border-top: 1px solid #444; margin-top: 1rem; margin-bottom: 1rem; }

            /* Sidebar */
            .stSidebar > div:first-child { background-color: #2a2a2a; border-radius: 0 10px 10px 0; border-right: 1px solid #444; }
            .stSidebar .stSlider, .stSidebar .stSelectbox, .stSidebar .stMultiselect, .stSidebar .stTextInput { margin-bottom: 1rem; }
            .stSidebar label, .stSidebar .stMarkdown { color: #EAEAEA !important; }
            .stSidebar .stButton>button { border-radius: 5px; }

            /* Input Fields */
            .stTextInput input, .stMultiSelect div[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div {
                border-radius: 5px !important; border: 1px solid #555 !important;
                background-color: #333 !important; color: #EAEAEA !important;
            }
            .stTextInput input:focus, .stMultiSelect div[data-baseweb="select"] > div:focus-within, .stSelectbox div[data-baseweb="select"] > div:focus-within {
                border-color: #007bff !important; box-shadow: 0 0 0 1px #007bff !important;
            }

            /* Movie Grid Items */
            div[data-testid="column"] { transition: transform 0.2s ease-in-out; }
            div[data-testid="column"]:hover { transform: scale(1.03); }
            div[data-testid="stImage"] img { border-radius: 5px; border: 1px solid #444; object-fit: cover; max-height: 350px; width: 100%; display: block; margin-bottom: 5px; }
            .no-poster-available { height: 350px; display: flex; align-items: center; justify-content: center; border: 1px dashed #555; border-radius: 5px; text-align: center; background-color: #2a2a2a; color: #aaa; margin-bottom: 10px; width: 100%;}
            div[data-testid="column"] div[data-testid="stVerticalBlock"] [data-testid="stMarkdownContainer"] p {
                font-weight: 500; text-align: center; min-height: 3em; display: flex; align-items: center; justify-content: center;
                line-height: 1.2; padding: 0 5px; color: #FFFFFF; margin-bottom: 8px; overflow-wrap: anywhere;
            }
             div[data-testid="column"] .stButton > button {
                 width: 100%; margin-top: 5px; margin-bottom: 15px; border-radius: 5px; padding: 4px 8px; font-size: 0.9em;
                 background-color: rgba(0, 0, 0, 0.3); color: #CCCCCC; border: 1px solid #555; text-align: center;
                 box-shadow: none; transition: all 0.2s ease; cursor: pointer; display: block;
             }
            div[data-testid="column"] .stButton > button:hover { background-color: rgba(255, 255, 255, 0.15); color: #FFFFFF; border-color: #777; }
            div[data-testid="column"] .stButton > button:active { background-color: rgba(255, 255, 255, 0.2); }
            div[data-testid="column"] .stButton > button:focus { box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.5) !important; outline: none; }
             p.rating-text-na { text-align: center; font-size: 0.9em; color: #888; margin-top: 5px; margin-bottom: 15px; padding: 4px 8px; }

            /* Movie Details View */
            .detail-item { margin-bottom: 0.6rem; line-height: 1.4; text-align: left; }
            .detail-item b { margin-right: 7px; color: #FFFFFF; }
            .detail-item i { color: #CCCCCC; }
            a.detail-link { margin-right: 15px; text-decoration: none; }

            /* Pagination & Back Buttons Common Styles */
            button[key^="prev_page_button"], button[key^="next_page_button"],
            button[key^="back_button"] {
                background-color: #555; color: #EAEAEA; border: 1px solid #777; border-radius: 5px;
                padding: 0.25rem 0.75rem; margin: 5px;
                transition: all 0.2s ease;
            }
            button[key^="prev_page_button"]:hover, button[key^="next_page_button"]:hover,
            button[key^="back_button"]:hover {
                 background-color: #666; border-color: #888; color: #FFFFFF;
            }
            button[key^="prev_page_button"]:disabled, button[key^="next_page_button"]:disabled {
                 background-color: #444; color: #888; border-color: #555; cursor: not-allowed; opacity: 0.65;
            }
            button[key^="prev_page_button"]:focus, button[key^="next_page_button"]:focus,
            button[key^="back_button"]:focus {
                 box-shadow: 0 0 0 0.2rem rgba(85, 85, 85, 0.5); outline: none;
            }

            /* Pagination Specific */
             div[data-testid="stHorizontalBlock"] {
                align-items: center; margin-top: 1.5rem;
             }
             div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stMarkdown p {
                 text-align: center !important; margin: 0; color: #CCCCCC; font-size: 0.95em;
             }

            /* Back Button Specific (Details View) */
            button[key^="back_button"] { margin-top: 10px; margin-bottom: 15px; float: left; }

            /* Alerts */
            .stAlert { border-radius: 5px; border-width: 1px; border-style: solid; }
            .stAlert[data-testid="stInfo"] { background-color: rgba(0, 123, 255, 0.1); border-color: rgba(0, 123, 255, 0.3); }
            .stAlert[data-testid="stWarning"] { background-color: rgba(255, 193, 7, 0.1); border-color: rgba(255, 193, 7, 0.3); }
            .stAlert[data-testid="stError"] { background-color: rgba(220, 53, 69, 0.1); border-color: rgba(220, 53, 69, 0.3); }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# --- Callback Functions ---
def set_selected_movie(movie_id: int):
    """Callback to set the selected movie ID and reset pagination/surprise."""
    st.session_state['selected_movie_id'] = movie_id
    if 'surprise_just_shown' in st.session_state:
         del st.session_state['surprise_just_shown']

def clear_selected_movie():
    """Callback for the 'Back' button from details view."""
    st.session_state['selected_movie_id'] = None

def trigger_surprise_me():
    """Callback for the 'Surprise Me!' button."""
    st.session_state['surprise_mode'] = True
    st.session_state['page'] = 1
    st.session_state['selected_movie_id'] = None
    if 'surprise_just_shown' in st.session_state:
         del st.session_state['surprise_just_shown']

# --- Helper Functions for Filtering ---
def _build_base_query_params(
    year_range: Tuple[int, int],
    selected_genre_names: List[str],
    selected_mood: str,
    min_rating: float,
    selected_language_names: List[str]
) -> Dict[str, Any]:
    """Builds the base dictionary of query parameters for the TMDB API."""
    query_params = {}
    if year_range:
        query_params['primary_release_date.gte'] = f"{year_range[0]}-01-01"
        query_params['primary_release_date.lte'] = f"{year_range[1]}-12-31"

    genre_ids_to_query = set()
    if GENRES:
        if "All" not in selected_genre_names:
            selected_ids = {g_id for g_id, g_name in GENRES.items() if g_name in selected_genre_names}
            genre_ids_to_query.update(selected_ids)
        if selected_mood != "All" and selected_mood in MOOD_TO_GENRE_IDS:
            genre_ids_to_query.update(MOOD_TO_GENRE_IDS[selected_mood])
    if genre_ids_to_query:
        query_params['with_genres'] = ",".join(map(str, genre_ids_to_query))

    if min_rating > 0:
        query_params['vote_average.gte'] = min_rating

    if selected_language_names and "Any" not in selected_language_names:
        selected_language_codes = [SUPPORTED_LANGUAGES[name] for name in selected_language_names if name in SUPPORTED_LANGUAGES]
        if selected_language_codes:
            query_params['with_original_language'] = "|".join(selected_language_codes)

    return query_params

def _get_person_id(person_name: str, person_type: str) -> Optional[int]:
    """Gets the ID for an actor or director, using session state for caching."""
    state_key_id = f'{person_type}_id_result'
    state_key_name = f'searched_{person_type}_name'
    cached_id = st.session_state.get(state_key_id)
    cached_name = st.session_state.get(state_key_name)
    if not person_name:
        st.session_state[state_key_id] = None
        st.session_state[state_key_name] = None
        return None
    if person_name == cached_name and cached_name is not None:
        if cached_id is None and person_name: pass
        return cached_id
    st.session_state[state_key_name] = person_name
    with st.spinner(f"Searching for {person_type} '{person_name}'..."):
        found_id = search_person(person_name)
        st.session_state[state_key_id] = found_id
        if found_id is None:
            st.warning(f"{person_type.capitalize()} '{person_name}' not found.")
        return found_id


# --- Main Application ---
def main():
    apply_custom_css()
    initialize_session_state()

    st.title("🍿 allaooaoa")

    # --- Sidebar ---
    with st.sidebar:
        st.header("🔍 Filter Recommendations")
        year_range = st.slider("Select Year Range:", MIN_YEAR, MAX_YEAR, DEFAULT_YEAR_RANGE)
        selected_genres = st.multiselect("Select Genres:", GENRE_OPTIONS, default=["All"])
        selected_mood = st.selectbox("Select Mood:", MOOD_OPTIONS, index=0)

        selected_languages = st.multiselect(
            "Select Original Language(s):",
            LANGUAGE_OPTIONS,
            default=["Any"],
        )

        actor_name = st.text_input("Search Actor:", placeholder="e.g., Tom Hanks", key="actor_search_input")
        director_name = st.text_input("Search Director:", placeholder="e.g., Christopher Nolan", key="director_search_input")
        min_rating = st.slider("Minimum Rating:", 0.0, 10.0, DEFAULT_MIN_RATING, step=0.1)
        st.markdown("---")
        st.button("🎁 Surprise Me!", on_click=trigger_surprise_me, use_container_width=True)
        st.markdown("---")


    # --- Main Content Area ---
    selected_movie_id = st.session_state.get('selected_movie_id')

    if selected_movie_id:
        # --- Movie Details View ---
        st.button("⬅️ Back to Recommendations", key="back_button_details", on_click=clear_selected_movie)
        with st.spinner(f"Loading details for movie ID {selected_movie_id}..."):
            movie_details = fetch_movie_details(selected_movie_id)
        if movie_details:
            display_movie_details(movie_details)
        else:
            st.error("Sorry, could not load movie details. The movie might not exist or there was an API issue.")

    else:
        # --- Movie Grid View ---
        current_page = st.session_state.get('page', 1)
        is_surprise_mode = st.session_state.get('surprise_mode', False)
        query_params = {}
        fetch_info_message = ""

        if is_surprise_mode:
            st.info("🎉 Surprise! Finding something unexpected for you...")
            surprise_query = {
                'sort_by': 'popularity.desc',
                'vote_average.gte': 7.0,
                'vote_count.gte': 300
            }
            if year_range:
                 surprise_query['primary_release_date.gte'] = f"{year_range[0]}-01-01"
                 surprise_query['primary_release_date.lte'] = f"{year_range[1]}-12-31"
            with st.spinner("Calculating surprise scope..."):
                 _, initial_total_pages = fetch_movies(surprise_query, page=1)
            max_page = min(initial_total_pages, MAX_API_PAGES) if initial_total_pages else 1
            page_to_fetch = random.randint(1, max_page) if max_page > 1 else 1
            fetch_info_message = f"*(Showing random page {page_to_fetch} of {max_page} highly-rated movies)*"
            with st.spinner(f"Unveiling movies from page {page_to_fetch}..."):
                 recommended_movies, total_pages = fetch_movies(surprise_query, page=page_to_fetch)
            st.session_state['page'] = page_to_fetch
            st.session_state['surprise_mode'] = False
            st.session_state['surprise_just_shown'] = True
            st.rerun()

        else:
            # --- Regular Grid View (Not Surprise) ---
            query_params = _build_base_query_params(
                year_range, selected_genres, selected_mood, min_rating, selected_languages
            )

            actor_id = _get_person_id(actor_name, "actor")
            director_id = _get_person_id(director_name, "director")
            person_id_to_query = None
            if actor_id and director_id:
                person_id_to_query = actor_id
                st.info(f"Showing results for actor '{actor_name}'. Director filter ignored as actor filter is active.", icon="🎭")
            elif actor_id:
                person_id_to_query = actor_id
            elif director_id:
                 query_params['with_crew'] = str(director_id)
            if actor_id:
                 query_params['with_people'] = str(actor_id)
                 if 'with_crew' in query_params: del query_params['with_crew']

            filters_applied = bool(query_params.get('with_genres') or
                                   person_id_to_query or
                                   query_params.get('with_crew') or
                                   query_params.get('vote_average.gte') or
                                   query_params.get('with_original_language'))

            if not filters_applied:
                query_params['sort_by'] = 'popularity.desc'
            page_to_fetch = st.session_state.get('page', 1)
            with st.spinner(f"Fetching movies (Page {page_to_fetch})..."):
                 recommended_movies, total_pages = fetch_movies(query_params, page=page_to_fetch)


        # --- Display Movie Grid ---
        if fetch_info_message: st.caption(fetch_info_message)

        if recommended_movies:
            if st.session_state.get('surprise_just_shown'):
                st.header("🎁 Surprise Movies!")
            elif filters_applied:
                st.header("🍿 Recommended Movies")
            else:
                st.header("🔥 Popular Movies")

            cols = st.columns(NUM_COLUMNS)
            for i, movie in enumerate(recommended_movies):
                with cols[i % NUM_COLUMNS]:
                    movie_id = movie.get('id')
                    title = movie.get('title', movie.get('name', 'N/A'))
                    poster_path = movie.get('poster_path')
                    rating = movie.get('vote_average')
                    vote_count = movie.get('vote_count')

                    st.markdown(f"<p>{html.escape(title)}</p>", unsafe_allow_html=True)

                    if poster_path and IMAGE_BASE_URL:
                         # *** UPDATED st.image call ***
                         st.image(f"{IMAGE_BASE_URL}{poster_path}", use_container_width=True)
                    else:
                         st.markdown(f"<div class='no-poster-available'>No Poster</div>", unsafe_allow_html=True)

                    formatted_rating_str = format_rating(rating, vote_count)
                    if formatted_rating_str != "N/A" and movie_id:
                        button_key = f"rating_btn_{movie_id}_{page_to_fetch}_{i}"
                        st.button(
                            f"⭐ {formatted_rating_str.split('/')[0]}",
                            key=button_key,
                            on_click=set_selected_movie,
                            args=(movie_id,),
                            use_container_width=True,
                            help=f"View details - Rating: {formatted_rating_str}"
                        )
                    else:
                        st.markdown(f"<p class='rating-text-na'>⭐ N/A</p>", unsafe_allow_html=True)

            # --- Pagination Controls ---
            st.write("")
            max_display_page = min(total_pages, MAX_API_PAGES) if total_pages else 1
            if max_display_page > 1:
                col_prev, col_page_info, col_next = st.columns([2, 3, 2])
                with col_prev:
                     st.button("⬅️ Previous", key="prev_page_button", disabled=(current_page <= 1), on_click=previous_page, use_container_width=True)
                with col_page_info:
                    st.markdown(f"<p>Page {current_page} of {max_display_page}</p>", unsafe_allow_html=True)
                with col_next:
                     st.button("Next ➡️", key="next_page_button", disabled=(current_page >= max_display_page), on_click=next_page, use_container_width=True)

        elif not recommended_movies and not is_surprise_mode:
             st.info("🤔 No movies found matching your current criteria. Try adjusting the filters or use 'Surprise Me'!")


# --- Run App ---
if __name__ == "__main__":
    if API_KEY and BASE_URL and IMAGE_BASE_URL:
        main()
    else:
         st.warning("Application cannot start due to configuration errors.")
