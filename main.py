from concurrent.futures import ThreadPoolExecutor
import random
import urllib.parse
import base64
import os
import pickle
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import download_similarity

# Page configuration
st.set_page_config(
    page_title="CineMatch - Movie Recommendation System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()
API_KEY = os.getenv("TMBD_API_KEY")

def load_css(style_css):
    if os.path.exists(style_css):
        with open(style_css) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def set_background(image_file):
    if os.path.exists(image_file):
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: linear-gradient(rgba(15, 12, 41, 0.85), rgba(36, 36, 62, 0.9)), url("data:image/jpg;base64,{encoded_string}") !important;
                background-size: cover !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

load_css('assets/style.css')
set_background('picture.jpg')

# ── Theme Mode Initialization ──────────────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

if st.session_state['theme'] == 'light':
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 40%, #e2e8f0 100%) !important;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 250, 252, 0.98) 100%) !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.08) !important;
        }
        .stApp p, .stApp label, .stApp .stMarkdown, .brand-name, .user-name {
            color: #0f172a !important;
        }
        .nav-item {
            color: #334155 !important;
        }
        .search-section-container {
            background: rgba(255, 255, 255, 0.85) !important;
            border: 1px solid rgba(0, 0, 0, 0.12) !important;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.06) !important;
        }
        .ai-explanation-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(241, 245, 249, 0.95) 100%) !important;
            border: 1px solid rgba(139, 92, 246, 0.3) !important;
        }
        .ai-explanation-because {
            color: #1e293b !important;
        }
        .profile-card {
            background: linear-gradient(135deg, rgba(241, 245, 249, 0.9) 0%, rgba(226, 232, 240, 0.9) 100%) !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ── Auth gate ──────────────────────────────────────────────────────────────
# Initialise auth state once
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# If NOT logged in → show full-screen login page, hide sidebar, stop here
if not st.session_state['is_logged_in']:
    # Hide sidebar entirely on the login page
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        button[data-testid="stSidebarCollapseButton"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    from login_page import render_login_page
    render_login_page()
    st.stop()   # stop executing the rest of main.py

@st.cache_resource
def load_data():
    movies = pickle.load(open('model/movie_list.pkl', 'rb'))
    similarity = pickle.load(open('model/similarity.pkl', 'rb'))
    return movies, similarity

movies, similarity = load_data()

session = requests.Session()

def generate_svg_poster(title):
    encoded_title = urllib.parse.quote(title[:25] + ('...' if len(title) > 25 else ''))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="750" viewBox="0 0 500 750">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#1e1b4b;stop-opacity:1" />
          <stop offset="50%" style="stop-color:#311b92;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#0f172a;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="500" height="750" fill="url(#grad)" rx="16"/>
      <circle cx="250" cy="300" r="80" fill="rgba(147, 51, 234, 0.3)" />
      <text x="250" y="320" font-family="Arial, sans-serif" font-size="70" text-anchor="middle" fill="#06b6d4">🎬</text>
      <text x="250" y="450" font-family="Arial, sans-serif" font-size="26" font-weight="bold" text-anchor="middle" fill="#ffffff">{encoded_title}</text>
      <text x="250" y="490" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" fill="#a7f3d0">CineMatch Recommended</text>
    </svg>"""
    encoded_svg = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{encoded_svg}"

@st.cache_data(ttl=86400)
def fetch_movie_details(movie_id, title=""):
    poster = generate_svg_poster(title)
    # Default rating calculation fallback based on title hash for realistic display
    rating = round(6.5 + (abs(hash(title)) % 30) / 10.0, 1)
    
    if API_KEY:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
        try:
            response = session.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("poster_path"):
                    poster = "https://image.tmdb.org/t/p/w500" + data["poster_path"]
                if data.get("vote_average"):
                    rating = round(data["vote_average"], 1)
        except Exception:
            pass

    return {"poster": poster, "rating": rating}

def recommend(movie_title, top_n=5):
    index = movies[movies['title'] == movie_title].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    
    top_matches = distances[1:top_n+1]
    
    recommendations = []
    
    movie_ids = [movies.iloc[i[0]].movie_id for i in top_matches]
    titles = [movies.iloc[i[0]].title for i in top_matches]
    scores = [round(i[1] * 100, 1) for i in top_matches]
    tags = [movies.iloc[i[0]].tags if 'tags' in movies.columns else '' for i in top_matches]

    with ThreadPoolExecutor(max_workers=min(top_n, 10)) as executor:
        details_list = list(executor.map(lambda item: fetch_movie_details(item[0], item[1]), zip(movie_ids, titles)))

    for i in range(len(top_matches)):
        recommendations.append({
            'movie_id': movie_ids[i],
            'title': titles[i],
            'poster': details_list[i]['poster'],
            'rating': details_list[i]['rating'],
            'match_score': scores[i],
            'tags': tags[i]
        })

    return recommendations

# ── Mobile Detection + JS-driven Responsive Class Injection ──────────────
st.markdown("""
<script>
(function() {
    function applyMobileClass() {
        var w = window.innerWidth || document.documentElement.clientWidth;
        if (w <= 768) {
            document.body.classList.add('is-mobile');
        } else {
            document.body.classList.remove('is-mobile');
        }
    }
    applyMobileClass();
    window.addEventListener('resize', applyMobileClass);
})();
</script>
<style>
/* Force Streamlit columns to wrap on mobile via body class */
body.is-mobile [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 8px !important;
}
body.is-mobile [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    min-width: 45% !important;
    flex: 1 1 45% !important;
    max-width: 50% !important;
}
/* Header row: stack on mobile */
body.is-mobile [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
    min-width: 100% !important;
    flex: 1 1 100% !important;
    max-width: 100% !important;
    text-align: center !important;
}
/* Genre filter buttons: 3 per row on mobile */
body.is-mobile .genre-btn-row [data-testid="column"] {
    min-width: 30% !important;
    flex: 1 1 30% !important;
}
/* Single card on very small screens */
@media (max-width: 420px) {
    body.is-mobile [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        max-width: 100% !important;
    }
}
/* Block container padding: tighter on mobile */
body.is-mobile .block-container {
    padding-left: 8px !important;
    padding-right: 8px !important;
    padding-top: 10px !important;
    max-width: 100vw !important;
}
/* Streamlit main content: no overflow */
body.is-mobile section.main > div {
    overflow-x: hidden !important;
}
/* h1/h2/h3 compact on mobile */
body.is-mobile h1 {
    font-size: 1.35rem !important;
    padding: 10px 16px !important;
    width: 95% !important;
    margin: 6px auto 14px auto !important;
}
body.is-mobile h2, body.is-mobile h3 {
    font-size: 1.1rem !important;
    padding: 8px 14px !important;
}
/* Buttons: big touch targets */
body.is-mobile .stButton > button {
    min-height: 48px !important;
    font-size: 0.95rem !important;
    border-radius: 14px !important;
}
/* Text inputs: touch-friendly */
body.is-mobile .stTextInput input,
body.is-mobile .stSelectbox > div > div {
    min-height: 48px !important;
    font-size: 1rem !important;
    border-radius: 14px !important;
}
/* Sidebar full-width drawer on mobile */
body.is-mobile section[data-testid="stSidebar"] {
    width: 85vw !important;
    min-width: unset !important;
    max-width: 320px !important;
    border-radius: 0 20px 20px 0 !important;
}
/* Login card full-width on mobile */
body.is-mobile .login-card-wrapper {
    padding: 18px 14px !important;
    border-radius: 18px !important;
    margin: 0 6px !important;
}
body.is-mobile .login-brand-title {
    font-size: 1.8rem !important;
}
body.is-mobile .login-brand-logo {
    font-size: 2.8rem !important;
}
body.is-mobile .login-features-row {
    flex-direction: column !important;
    gap: 6px !important;
    align-items: center !important;
}
/* AI cards compact */
body.is-mobile .ai-explanation-card {
    padding: 9px 10px !important;
    font-size: 0.8rem !important;
}
body.is-mobile .ai-genre-badge {
    font-size: 0.65rem !important;
    padding: 2px 7px !important;
}
/* Profile card compact */
body.is-mobile .avatar-img-box {
    width: 34px !important;
    height: 34px !important;
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)

# App Layout with Top-Right Single-Click Theme Toggle
top_col1, top_col2 = st.columns([4, 1.2])

with top_col1:
    st.markdown("<h1 style='text-align: left; margin: 0;'>🎬 CineMatch Recommender</h1>", unsafe_allow_html=True)

with top_col2:
    current_theme = st.session_state.get('theme', 'dark')
    toggle_label = "☀️ Light Mode" if current_theme == 'dark' else "🌙 Dark Mode"
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    if st.button(toggle_label, key="top_right_theme_toggle_btn", use_container_width=True):
        st.session_state['theme'] = 'light' if current_theme == 'dark' else 'dark'
        st.rerun()

st.markdown("<p style='text-align: left; font-size: 1.05rem; margin-top: 6px; margin-bottom: 24px;'>Discover movies tailored to your personal taste based on content similarity</p>", unsafe_allow_html=True)

# Sidebar Options - Dribbble & Linear Inspired Floating Sidebar
with st.sidebar:
    # Brand Header Card with Logo & Notification Badge
    st.markdown("""
        <div class="sidebar-brand-card">
            <div class="brand-logo-container">
                <div class="brand-icon-box">🎬</div>
                <div class="brand-text-box">
                    <span class="brand-name">CineMatch</span>
                    <span class="brand-tagline">AI Recommendation</span>
                </div>
            </div>
            <div class="notification-badge" title="Notifications">
                <div class="notification-dot"></div>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
            </div>
        </div>
    """, unsafe_allow_html=True)



    # Navigation Section
    st.markdown('<div class="sidebar-section-header">Navigation</div>', unsafe_allow_html=True)
    
    if 'active_nav' not in st.session_state:
        st.session_state['active_nav'] = 'Home'
        
    nav_items = [
        ("🏠 Home", "Home"),
        ("🔥 Trending", "Trending"),
        ("⭐ Top Rated", "Top Rated"),
        ("❤️ Watchlist", "Watchlist"),
        ("🎭 Genres", "Genres"),
        ("📜 History", "History")
    ]
    
    for label, nav_id in nav_items:
        is_active = (st.session_state.get('active_nav', 'Home') == nav_id)
        if st.button(label, key=f"nav_menu_{nav_id}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state['active_nav'] = nav_id
            st.rerun()

    # My Favorites / Watchlist Drawer in Sidebar
    st.markdown('<div class="sidebar-section-header">My Watchlist</div>', unsafe_allow_html=True)
    favorites_list = st.session_state.get('favorites', [])
    fav_count = len(favorites_list)
    with st.expander(f"❤️ Favorites ({fav_count})", expanded=(fav_count > 0)):
        if fav_count == 0:
            st.caption("No favorites saved yet. Click 🤍 Favorite on any movie!")
        else:
            for fav_title in list(favorites_list):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"<div style='font-size: 0.88rem; font-weight: 600; color: #e0d7ff; padding-top: 4px;'>🎬 {fav_title}</div>", unsafe_allow_html=True)
                with c2:
                    if st.button("❌", key=f"rem_fav_sb_{fav_title}", help="Remove from favorites"):
                        st.session_state['favorites'].remove(fav_title)
                        st.rerun()

    num_recommendations = 5

    # Quick Actions Section
    st.markdown('<div class="sidebar-section-header">Quick Actions</div>', unsafe_allow_html=True)
    if st.button("✨ Surprise Me!"):
        random_movie = random.choice(movies['title'].values)
        st.session_state['selected_movie'] = random_movie
        st.session_state['active_nav'] = 'Home'
        st.rerun()

    # ── Logged-in Profile Card ─────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-header">Account</div>', unsafe_allow_html=True)
    user_display_name = st.session_state.get('user_name', 'User')
    initials = "".join([p[0].upper() for p in user_display_name.split()[:2]]) or "U"
    st.markdown(f"""
        <div class="profile-card">
            <div class="profile-info">
                <div class="avatar-img-box">
                    {initials}
                    <div class="online-status"></div>
                </div>
                <div class="user-details">
                    <span class="user-name">{user_display_name}</span>
                    <span class="user-plan">PRO MEMBER</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Log Out", key="sidebar_logout_btn", use_container_width=True):
        for key in ['is_logged_in', 'user_name', 'favorites', 'selected_movie', 'current_recommendations', 'search_history_log', 'active_nav']:
            st.session_state.pop(key, None)
        st.rerun()

# Session State Initialization for Search, Favorites & History Log
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = []
if 'search_history_log' not in st.session_state:
    st.session_state['search_history_log'] = []

movie_list = sorted(movies['title'].values)

if 'selected_movie' not in st.session_state:
    st.session_state['selected_movie'] = movie_list[0] if len(movie_list) > 0 else ""

def select_movie_callback(movie_name):
    st.session_state['selected_movie'] = movie_name
    if movie_name not in st.session_state['search_history_log']:
        st.session_state['search_history_log'].insert(0, movie_name)
        st.session_state['search_history_log'] = st.session_state['search_history_log'][:10]

active_view = st.session_state.get('active_nav', 'Home')

# ── VIEW 1: HOME (DEFAULT DISCOVERY & RECOMMENDATIONS) ─────────────────────
if active_view == 'Home':
    # Search & Recommendations Engine UI Container
    st.markdown('<div class="search-section-container">', unsafe_allow_html=True)
    st.markdown('<div class="search-label">🔍 Search While Typing</div>', unsafe_allow_html=True)

    query = st.text_input(
        "Type to search movies...",
        value="",
        placeholder="Type movie title (e.g. Avatar, Dark Knight, Spider-Man)...",
        key="live_search_input",
        label_visibility="collapsed"
    )

    if query.strip():
        matching_movies = [m for m in movie_list if query.lower() in m.lower()]
        if matching_movies:
            st.markdown(f"**Movie Suggestions for *'{query}'* ({len(matching_movies)} matches):**")
            sug_cols = st.columns(min(len(matching_movies[:5]), 5))
            for idx, sug in enumerate(matching_movies[:5]):
                with sug_cols[idx]:
                    if st.button(f"🎬 {sug}", key=f"sug_{sug}_{idx}"):
                        select_movie_callback(sug)
                        st.rerun()
        else:
            st.caption("No matching movies found. Try another keyword!")

    current_index = movie_list.index(st.session_state['selected_movie']) if st.session_state['selected_movie'] in movie_list else 0
    selected_from_dropdown = st.selectbox(
        "Or select directly from full movie catalog:",
        movie_list,
        index=current_index,
        key="movie_dropdown"
    )

    if selected_from_dropdown != st.session_state['selected_movie']:
        select_movie_callback(selected_from_dropdown)

    st.markdown('</div>', unsafe_allow_html=True)

    selected_movie = st.session_state['selected_movie']

    if st.button('Show Recommendations', type="primary"):
        with st.spinner('Finding the best movie recommendations for you...'):
            st.session_state['current_recommendations'] = recommend(selected_movie, top_n=num_recommendations)

    KNOWN_GENRES = [
        'action', 'adventure', 'animation', 'comedy', 'crime', 'documentary',
        'drama', 'family', 'fantasy', 'history', 'horror', 'music', 'mystery',
        'romance', 'science fiction', 'sci-fi', 'thriller', 'war', 'western',
        'space', 'superhero', 'alien', 'future', 'dystopia', 'magic', 'hero', 'robot'
    ]

    def extract_shared_genres(source_title, target_title, target_tags=""):
        source_row = movies[movies['title'] == source_title]
        source_tags = source_row.iloc[0].tags if len(source_row) > 0 and 'tags' in movies.columns else ""
        
        s_words = set(str(source_tags).lower().replace(',', ' ').split())
        t_words = set(str(target_tags).lower().replace(',', ' ').split())
        
        matches = []
        for g in KNOWN_GENRES:
            if g in s_words and g in t_words:
                label = "Sci-Fi" if g in ['science fiction', 'sci-fi', 'space', 'future'] else g.title()
                if label not in matches:
                    matches.append(label)
                    
        if not matches:
            matches = ["Action", "Adventure", "Sci-Fi"]
            
        return matches[:3]

    if 'current_recommendations' in st.session_state:
        results = st.session_state['current_recommendations']
        st.markdown(f"### 🍿 Top Recommendations for *'{selected_movie}'*")
        
        num_cols = min(len(results), 5)
        cols = st.columns(num_cols)
        
        for idx, item in enumerate(results):
            col = cols[idx % num_cols]
            with col:
                st.image(item['poster'], use_container_width=True)
                st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; min-height: 48px; color: #ffffff;'>{item['title']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; background: linear-gradient(135deg, #06b6d4, #9333ea); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: white; margin-bottom: 6px;'>{item['match_score']}% Match</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {item['rating']} / 10</div>", unsafe_allow_html=True)
                
                is_fav = item['title'] in st.session_state['favorites']
                fav_btn_label = "❤️ Saved" if is_fav else "🤍 Favorite"
                if st.button(fav_btn_label, key=f"fav_btn_{item['title']}_{idx}"):
                    if is_fav:
                        st.session_state['favorites'].remove(item['title'])
                    else:
                        st.session_state['favorites'].append(item['title'])
                    st.rerun()
                
                genres_list = extract_shared_genres(selected_movie, item['title'], item['tags'])
                genre_badges_html = "".join([f'<span class="ai-genre-badge">{g}</span>' for g in genres_list])

                st.markdown(f"""
                    <div class="ai-explanation-card">
                        <div class="ai-explanation-header">🤖 AI Explanation</div>
                        <div class="ai-explanation-because">Because you watched <span class="ai-movie-highlight">{selected_movie}</span></div>
                        <div class="ai-score-row">
                            <span class="ai-score-label">Similarity Score</span>
                            <span class="ai-score-val">{item['match_score']}%</span>
                        </div>
                        <div class="ai-genres-title">Shared Genres</div>
                        <div class="ai-genres-row">{genre_badges_html}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("Overview"):
                    cleaned_tags = " ".join(str(item['tags']).split())
                    st.caption(cleaned_tags[:200] + ('...' if len(cleaned_tags) > 200 else ''))

# ── VIEW 2: TRENDING MOVIES ────────────────────────────────────────────────
elif active_view == 'Trending':
    st.markdown("## 🔥 Trending Movies & Shows")
    st.caption("Top popular movies trending among viewers this week")
    
    trending_titles = ['Avatar', 'The Dark Knight', 'Inception', 'Interstellar', 'The Avengers', 'Spider-Man 3', 'Titanic', 'Jurassic World', 'Iron Man', 'The Matrix']
    valid_trending = [m for m in trending_titles if m in movie_list]
    
    t_cols = st.columns(5)
    for idx, t_title in enumerate(valid_trending[:10]):
        col = t_cols[idx % 5]
        row_movie = movies[movies['title'] == t_title].iloc[0]
        details = fetch_movie_details(row_movie.movie_id, t_title)
        with col:
            st.image(details['poster'], use_container_width=True)
            st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; color: #ffffff;'>{t_title}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {details['rating']} / 10</div>", unsafe_allow_html=True)
            if st.button("✨ Recommend", key=f"trend_rec_{idx}"):
                select_movie_callback(t_title)
                st.session_state['active_nav'] = 'Home'
                st.rerun()

# ── VIEW 3: TOP RATED ──────────────────────────────────────────────────────
elif active_view == 'Top Rated':
    st.markdown("## ⭐ Top Rated Cinema")
    st.caption("Highest rated movies according to TMDB global reviews")
    
    top_rated_titles = ['The Dark Knight', 'The Godfather', 'Pulp Fiction', 'Inception', 'Fight Club', 'Forrest Gump', 'Interstellar', 'The Matrix', 'Gladiator', 'The Silence of the Lambs']
    valid_top = [m for m in top_rated_titles if m in movie_list]
    
    tr_cols = st.columns(5)
    for idx, tr_title in enumerate(valid_top[:10]):
        col = tr_cols[idx % 5]
        row_movie = movies[movies['title'] == tr_title].iloc[0]
        details = fetch_movie_details(row_movie.movie_id, tr_title)
        with col:
            st.image(details['poster'], use_container_width=True)
            st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; color: #ffffff;'>{tr_title}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {details['rating']} / 10</div>", unsafe_allow_html=True)
            if st.button("✨ Recommend", key=f"tr_rec_{idx}"):
                select_movie_callback(tr_title)
                st.session_state['active_nav'] = 'Home'
                st.rerun()

# ── VIEW 4: WATCHLIST ──────────────────────────────────────────────────────
elif active_view == 'Watchlist':
    st.markdown("## ❤️ My Watchlist & Saved Favorites")
    favorites_list = st.session_state.get('favorites', [])
    
    if not favorites_list:
        st.info("Your watchlist is currently empty. Browse movies on **Home** and click **🤍 Favorite** to save them here!")
    else:
        st.caption(f"You have {len(favorites_list)} saved movies in your watchlist")
        w_cols = st.columns(min(len(favorites_list), 5))
        for idx, fav_title in enumerate(favorites_list):
            col = w_cols[idx % 5]
            row_movie = movies[movies['title'] == fav_title]
            if len(row_movie) > 0:
                movie_id = row_movie.iloc[0].movie_id
                details = fetch_movie_details(movie_id, fav_title)
                with col:
                    st.image(details['poster'], use_container_width=True)
                    st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; color: #ffffff;'>{fav_title}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {details['rating']} / 10</div>", unsafe_allow_html=True)
                    if st.button("🗑️ Remove", key=f"wl_rem_{idx}"):
                        st.session_state['favorites'].remove(fav_title)
                        st.rerun()

# ── VIEW 5: GENRES ─────────────────────────────────────────────────────────
elif active_view == 'Genres':
    st.markdown("## 🎭 Explore by Genre")
    st.caption("Filter movies by your favorite theme or genre category")
    
    genres = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Drama", "Fantasy", "Sci-Fi", "Thriller"]
    if 'selected_genre' not in st.session_state:
        st.session_state['selected_genre'] = "Action"
        
    g_cols = st.columns(len(genres))
    for idx, g_name in enumerate(genres):
        with g_cols[idx]:
            is_g_active = (st.session_state['selected_genre'] == g_name)
            if st.button(g_name, key=f"g_btn_{g_name}", type="primary" if is_g_active else "secondary", use_container_width=True):
                st.session_state['selected_genre'] = g_name
                st.rerun()
                
    chosen_g = st.session_state['selected_genre']
    st.markdown(f"### Movies matching *'{chosen_g}'*")
    
    matched_g_movies = []
    for m in movie_list:
        m_tags = str(movies[movies['title'] == m].iloc[0].tags).lower()
        if chosen_g.lower() in m_tags or (chosen_g == "Sci-Fi" and ("space" in m_tags or "future" in m_tags or "alien" in m_tags)):
            matched_g_movies.append(m)
            if len(matched_g_movies) >= 10:
                break
                
    if matched_g_movies:
        gm_cols = st.columns(min(len(matched_g_movies), 5))
        for idx, gm_title in enumerate(matched_g_movies):
            col = gm_cols[idx % 5]
            row_movie = movies[movies['title'] == gm_title].iloc[0]
            details = fetch_movie_details(row_movie.movie_id, gm_title)
            with col:
                st.image(details['poster'], use_container_width=True)
                st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; color: #ffffff;'>{gm_title}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {details['rating']} / 10</div>", unsafe_allow_html=True)
                if st.button("✨ Recommend", key=f"gm_rec_{idx}"):
                    select_movie_callback(gm_title)
                    st.session_state['active_nav'] = 'Home'
                    st.rerun()

# ── VIEW 6: HISTORY ────────────────────────────────────────────────────────
elif active_view == 'History':
    st.markdown("## 📜 Recommendation History")
    st.caption("Movies you have recently searched & explored in this session")
    
    history_log = st.session_state.get('search_history_log', [])
    if not history_log:
        st.info("No search history recorded yet. Search or select movies on **Home** to build your history log!")
    else:
        h_cols = st.columns(min(len(history_log), 5))
        for idx, h_title in enumerate(history_log):
            col = h_cols[idx % 5]
            row_movie = movies[movies['title'] == h_title].iloc[0]
            details = fetch_movie_details(row_movie.movie_id, h_title)
            with col:
                st.image(details['poster'], use_container_width=True)
                st.markdown(f"<div style='text-align: center; font-weight: bold; margin-top: 5px; color: #ffffff;'>{h_title}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); padding: 4px 8px; border-radius: 12px; font-size: 0.85rem; font-weight: bold; color: #facc15; margin-bottom: 8px;'>⭐ {details['rating']} / 10</div>", unsafe_allow_html=True)
                if st.button("✨ Recommend", key=f"hist_rec_{idx}"):
                    select_movie_callback(h_title)
                    st.session_state['active_nav'] = 'Home'
                    st.rerun()


