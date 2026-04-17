import stripe
from config import get_secret


def create_checkout_session(email: str) -> str:
    """Create a Stripe Checkout session and return the redirect URL."""
    stripe.api_key = get_secret("STRIPE_SECRET_KEY")
    price_id = get_secret("STRIPE_PRICE_ID")
    base_url = get_secret("STREAMLIT_URL", "https://pulseweb.streamlit.app")
    if not stripe.api_key or not price_id:
        raise ValueError("Stripe is not configured. Add STRIPE_SECRET_KEY and STRIPE_PRICE_ID to Streamlit Cloud Secrets, then reboot the app.")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=email,
        success_url=f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}?page=pricing",
    )
    return session.url


def verify_session(session_id: str) -> dict:
    """Retrieve a Stripe Checkout session. Returns email + subscription_id if paid, else {}."""
    stripe.api_key = get_secret("STRIPE_SECRET_KEY")
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status == "paid":
        return {
            "email": session.customer_details.email,
            "subscription_id": session.subscription,
        }
    return {}
