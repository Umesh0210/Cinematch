import streamlit as st
import hashlib
import db

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def render_login_page():
    # Initialize DB schema automatically
    success, db_msg = db.init_db()
    if not success:
        st.warning(f"⚠️ MySQL Connection Notice: {db_msg}. Please check if MySQL server is running on port 3306.")

    st.markdown("""
        <div class="login-hero-container">
            <div class="login-brand-logo">🎬</div>
            <div class="login-brand-title">CineMatch</div>
            <div class="login-brand-subtitle">AI-Powered Movie &amp; Show Recommendation Platform</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown('<div class="login-card-wrapper">', unsafe_allow_html=True)
        tab_sign_in, tab_sign_up = st.tabs(["🔐 Sign In", "📝 Sign Up"])

        # ── Sign Up ────────────────────────────────────────────────────────
        with tab_sign_up:
            with st.form("signup_form"):
                new_name  = st.text_input("Full Name",        placeholder="Alex Rivera",       key="su_name")
                new_email = st.text_input("Email Address",    placeholder="alex@example.com",  key="su_email")
                new_pass  = st.text_input("Create Password",  placeholder="••••••••",          key="su_pass",  type="password")
                new_pass2 = st.text_input("Confirm Password", placeholder="••••••••",          key="su_pass2", type="password")
                signup_submit = st.form_submit_button("🎉 Create Account", use_container_width=True, type="primary")

            if signup_submit:
                email_clean = new_email.strip().lower()

                if not new_name.strip():
                    st.error("Please enter your full name.")
                elif not email_clean:
                    st.error("Please enter a valid email address.")
                elif not new_pass:
                    st.error("Please create a password.")
                elif new_pass != new_pass2:
                    st.error("Passwords do not match.")
                elif db.user_exists(email_clean):
                    st.warning("An account with this email already exists in MySQL. Please sign in.")
                else:
                    ok, reg_msg = db.register_user(email_clean, new_name.strip(), _hash(new_pass))
                    if ok:
                        st.success(f"✅ Account created for **{new_name.strip()}** in MySQL! Switch to **Sign In** to continue.")
                    else:
                        st.error(f"Failed to register account: {reg_msg}")

        # ── Sign In ────────────────────────────────────────────────────────
        with tab_sign_in:
            with st.form("login_form"):
                email    = st.text_input("Email Address", placeholder="alex@example.com", key="li_email")
                password = st.text_input("Password",      placeholder="••••••••",         key="li_pass", type="password")

                c1, c2 = st.columns(2)
                with c1:
                    submit = st.form_submit_button("🚀 Sign In", use_container_width=True, type="primary")
                with c2:
                    demo   = st.form_submit_button("✨ Quick Demo", use_container_width=True)

            if submit:
                email_clean = email.strip().lower()

                if not email_clean or not password:
                    st.error("Please enter both email and password.")
                else:
                    user_record = db.get_user(email_clean)
                    if not user_record:
                        st.error("No account found with this email. Please sign up first.")
                    elif user_record['password_hash'] != _hash(password):
                        st.error("Incorrect password. Please try again.")
                    else:
                        st.session_state['is_logged_in'] = True
                        st.session_state['user_name']    = user_record['full_name']
                        st.rerun()

            if demo:
                st.session_state['is_logged_in'] = True
                st.session_state['user_name']    = "Demo User"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
            <div class="login-features-row">
                <span class="login-feature-tag">⚡ Real-Time Content AI</span>
                <span class="login-feature-tag">⭐ TMDB Live Ratings</span>
                <span class="login-feature-tag">❤️ Personal Watchlist</span>
            </div>
        """, unsafe_allow_html=True)
