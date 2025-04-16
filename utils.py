# utils.py

import streamlit as st
from PIL import Image
from io import BytesIO
import requests
from requests.exceptions import RequestException
from typing import Optional # Added for type hinting

try:
    from config import IMAGE_BASE_URL
except ImportError:
    st.error("Failed to import config.py in utils.py.")
    IMAGE_BASE_URL = None

def _display_poster(poster_path: str | None):
    """Displays the movie poster or a placeholder."""
    if poster_path and IMAGE_BASE_URL:
        image_url = f"{IMAGE_BASE_URL}{poster_path}"
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            st.image(image, use_column_width=True, output_format='JPEG')
        except RequestException as e:
            st.warning(f"⚠️ Could not load image: {e}", icon="🖼️")
        except Exception as img_err: # Catch potential PIL errors
            st.warning(f"⚠️ Error processing image: {img_err}", icon="🖼️")
    else:
        # Using st.markdown for placeholder to allow CSS styling from main.py
        st.markdown("<div class='no-poster-available' style='height: 450px;'>No Poster Available</div>", unsafe_allow_html=True)

def _format_runtime(runtime: int | None) -> str:
    """Formats runtime in minutes to 'Xh Ym' or 'Ym'."""
    if runtime and isinstance(runtime, int) and runtime > 0:
        hours = runtime // 60
        minutes = runtime % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    return "N/A"

# Renamed: Removed leading underscore
def format_rating(rating: float | None, vote_count: int | None) -> str:
    """Formats rating and vote count."""
    if rating and isinstance(rating, (int, float)) and rating > 0:
        formatted_rating = f"{rating:.1f}/10"
        if vote_count and isinstance(vote_count, int) and vote_count > 0:
            return f"{formatted_rating} ({vote_count:,} votes)"
        return formatted_rating
    return "N/A"

def display_movie_details(movie: dict):
    """Displays movie details (poster, title, overview, etc.) in Streamlit."""
    if not isinstance(movie, dict):
        st.error("Invalid movie data received.")
        return

    title = movie.get('title', movie.get('name', 'No Title Available'))
    st.header(f"🎬 {title}")

    col1, col2 = st.columns([1, 2]) # Ratio 1:2 for poster:details

    with col1:
        _display_poster(movie.get('poster_path')) # Keep internal helper for poster

    with col2:
        st.subheader("Details")

        # Prepare details data
        release_date = movie.get('release_date', '')
        genres = [genre['name'] for genre in movie.get('genres', [])]

        details_map = {
            "🗓️ Release Year": release_date[:4] if release_date and len(release_date) >= 4 else 'N/A',
            "🎭 Genres": ', '.join(genres) if genres else 'N/A',
             # Use the renamed public function here as well
            "⭐ Rating": format_rating(movie.get('vote_average'), movie.get('vote_count')),
            "⏱️ Runtime": _format_runtime(movie.get('runtime')), # Keep internal helper for runtime
            "💬 Tagline": f"<i>{movie.get('tagline')}</i>" if movie.get('tagline') else None
        }

        for key, value in details_map.items():
            if value:
                 st.markdown(f"<div class='detail-item'><b>{key}:</b> {value}</div>", unsafe_allow_html=True)

        st.markdown("---")

        st.subheader("Overview")
        overview = movie.get('overview', 'No overview available.')
        st.markdown(f"<p style='text-align: justify;'>{overview}</p>", unsafe_allow_html=True)

        homepage = movie.get('homepage')
        imdb_id = movie.get('imdb_id')
        links_html_parts = []
        if homepage:
            links_html_parts.append(f"<a href='{homepage}' target='_blank' class='detail-link'>🔗 Website</a>")
        if imdb_id and imdb_id.strip():
             links_html_parts.append(f"<a href='https://www.imdb.com/title/{imdb_id}/' target='_blank' class='detail-link'>🎬 IMDb</a>")

        if links_html_parts:
             st.markdown("---")
             st.markdown(" ".join(links_html_parts), unsafe_allow_html=True)


def previous_page():
    """Decrements the page number in session state if possible."""
    if st.session_state.get('page', 1) > 1:
        st.session_state['page'] -= 1
        if 'surprise_just_shown' in st.session_state:
             del st.session_state['surprise_just_shown']

def next_page():
    """Increments the page number in session state."""
    st.session_state['page'] = st.session_state.get('page', 1) + 1
    if 'surprise_just_shown' in st.session_state:
         del st.session_state['surprise_just_shown']