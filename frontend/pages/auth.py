"""
Authentication pages: Login, Registration, Forgot Password.
"""
from __future__ import annotations

import streamlit as st

from backend.auth.auth_manager import (
    register_user,
    login_user,
    request_password_reset,
    reset_password,
)


def render_auth_page():
    """Render the authentication page with Login/Register/Forgot tabs."""

    # Center the auth card
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # App branding
        st.markdown("""
        <div style="text-align:center; margin-bottom:2rem; margin-top:2rem;">
            <div style="font-size:3.5rem; margin-bottom:0.5rem;">🩺</div>
            <h1 style="background: linear-gradient(135deg, #1565C0, #43A047);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       background-clip: text; font-size:2rem; font-weight:800; margin:0;">
                MediVision AI
            </h1>
            <p style="color:#78909C; margin-top:0.25rem;">
                AI-Powered Medical Report Analyzer
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Auth mode selector
        if "auth_mode" not in st.session_state:
            st.session_state.auth_mode = "login"

        # Tab-like navigation
        auth_tabs = st.tabs(["🔐 Login", "📝 Register", "🔑 Forgot Password"])

        # ─── Login Tab ───
        with auth_tabs[0]:
            _render_login_form()

        # ─── Register Tab ───
        with auth_tabs[1]:
            _render_register_form()

        # ─── Forgot Password Tab ───
        with auth_tabs[2]:
            _render_forgot_password_form()


def _render_login_form():
    """Render the login form."""
    st.markdown("""
    <div style="text-align:center; margin-bottom:1rem;">
        <h3 style="color:#1565C0; font-weight:700;">Welcome Back</h3>
        <p style="color:#78909C; font-size:0.9rem;">Sign in to your account</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input(
            "Email Address",
            placeholder="you@example.com",
            key="login_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
        )

        submitted = st.form_submit_button(
            "🔐 Sign In",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                success, message, user = login_user(email, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.current_page = "Home"
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    # Google Login placeholder
    st.markdown('<div class="divider-text">or continue with</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="google-btn" onclick="alert('Google OAuth not configured. See README for setup instructions.')">
        <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
            <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
            <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
            <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
        </svg>
        Sign in with Google
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p style="text-align:center; color:#B0BEC5; font-size:0.8rem; margin-top:1rem;">
        <em>Google OAuth requires configuration. See documentation for setup.</em>
    </p>
    """, unsafe_allow_html=True)


def _render_register_form():
    """Render the registration form."""
    st.markdown("""
    <div style="text-align:center; margin-bottom:1rem;">
        <h3 style="color:#1565C0; font-weight:700;">Create Account</h3>
        <p style="color:#78909C; font-size:0.9rem;">Join MediVision AI to analyze your reports</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        full_name = st.text_input(
            "Full Name",
            placeholder="John Doe",
            key="reg_name",
        )
        email = st.text_input(
            "Email Address",
            placeholder="you@example.com",
            key="reg_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="At least 6 characters",
            key="reg_password",
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password",
            key="reg_confirm",
        )

        submitted = st.form_submit_button(
            "📝 Create Account",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message, user = register_user(email, full_name, password)
                if success:
                    st.success(message)
                    st.info("Please switch to the **Login** tab to sign in.")
                else:
                    st.error(message)


def _render_forgot_password_form():
    """Render the forgot password form."""
    st.markdown("""
    <div style="text-align:center; margin-bottom:1rem;">
        <h3 style="color:#1565C0; font-weight:700;">Reset Password</h3>
        <p style="color:#78909C; font-size:0.9rem;">Enter your email to receive a reset token</p>
    </div>
    """, unsafe_allow_html=True)

    # Step 1: Request token
    with st.form("forgot_form", clear_on_submit=False):
        email = st.text_input(
            "Email Address",
            placeholder="you@example.com",
            key="forgot_email",
        )

        submitted = st.form_submit_button(
            "📧 Send Reset Token",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not email:
                st.error("Please enter your email address.")
            else:
                success, message = request_password_reset(email)
                if success:
                    st.success(message)
                    st.info("💡 **Check the terminal/console** for the reset token.")
                else:
                    st.error(message)

    st.markdown("---")
    st.markdown("**Have a reset token?** Enter it below:")

    # Step 2: Use token to reset
    with st.form("reset_form", clear_on_submit=False):
        token = st.text_input(
            "Reset Token",
            placeholder="Paste your reset token here",
            key="reset_token",
        )
        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="At least 6 characters",
            key="reset_new_pw",
        )

        reset_submitted = st.form_submit_button(
            "🔑 Reset Password",
            use_container_width=True,
            type="primary",
        )

        if reset_submitted:
            if not token or not new_password:
                st.error("Please fill in all fields.")
            else:
                success, message = reset_password(token, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
