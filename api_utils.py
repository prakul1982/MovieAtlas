# api_utils.py

import requests
import json
import streamlit as st
from requests.exceptions import RequestException, JSONDecodeError

try:
    # API_KEY variable now expected to hold the v4 Bearer Token
    from config import API_KEY, BASE_URL
except ImportError:
    st.error("Failed to import config.py in api_utils.py.")
    API_KEY = None
    BASE_URL = None

# --- Standard Headers for TMDB API v4 ---
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}" if API_KEY else None
}
REQUEST_TIMEOUT = 15 # Slightly increased default timeout


def _make_api_request(url, params=None, method="GET"):
    """Helper function to make API requests with consistent error handling."""
    if not API_KEY or not BASE_URL or not HEADERS["Authorization"]:
        st.error("API Key or Base URL is not configured correctly.")
        return None # Indicate configuration error

    try:
        response = requests.request(method, url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except RequestException as e:
        status_code = e.response.status_code if e.response is not None else "N/A"
        st.error(f"API Request Failed ({url}): Status {status_code} - {e}")
        # Optionally log detailed error: print(f"Error details: {e}")
        return None # Indicate request error
    except JSONDecodeError:
        st.error(f"API Response Error ({url}): Could not decode JSON.")
        return None # Indicate JSON error


@st.cache_data
def load_genres():
    """Fetches and caches the movie genre list from the API."""
    if not BASE_URL: return {}
    url = f"{BASE_URL}/genre/movie/list"
    data = _make_api_request(url)
    if data and 'genres' in data:
        return {genre['id']: genre['name'] for genre in data['genres']}
    return {}


@st.cache_data
def search_person(name: str):
    """Searches for a person (actor/director) by name and returns their ID."""
    if not BASE_URL or not name: return None
    url = f"{BASE_URL}/search/person"
    params = {'query': name, 'include_adult': 'false'}
    data = _make_api_request(url, params=params)
    if data and data.get('results'):
        # Consider adding logic here to handle multiple results if needed
        # For simplicity, taking the first result as before.
        return data['results'][0]['id']
    elif data is not None: # Request succeeded but no results
        print(f"Person search for '{name}' returned no results.")
    # else: _make_api_request already showed an error
    return None


@st.cache_data
def fetch_movies(query_params: dict, page: int = 1):
    """Fetches a page of movies based on discovery filters."""
    if not BASE_URL: return [], 0
    url = f"{BASE_URL}/discover/movie"

    params = query_params.copy()
    params['page'] = page
    params['include_adult'] = 'false'
    params['language'] = 'en-US'
    # Ensure sort_by is present if needed, TMDB defaults might apply otherwise
    if 'sort_by' not in params:
         params['sort_by'] = 'popularity.desc' # Default sort if not specified

    data = _make_api_request(url, params=params)

    if data:
        return data.get('results', []), data.get('total_pages', 0)
    return [], 0 # Return empty if request failed


@st.cache_data
def fetch_movie_details(movie_id: int):
    """Fetches detailed information for a specific movie ID."""
    if not BASE_URL or not movie_id: return None
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {'language': 'en-US', 'append_to_response': 'credits'} # Append credits for potential future use
    data = _make_api_request(url, params=params)
    return data # Returns the JSON data or None if error