import streamlit as st
import requests

# Set up backend URL
BASE_URL = "http://localhost:8000"  # Adjust this to match your backend server


# Fetch all users from the JSON file
def get_all_users():
    response = requests.get(f"{BASE_URL}/get_users")
    return response.json()


# Fetch user balance from backend
def get_user_balance(user_id):
    response = requests.get(f"{BASE_URL}/user/{user_id}")
    if response.status_code == 200:
        return response.json().get("request_balance", 0)
    else:
        st.error("Error fetching balance.")
        return 0


# Run paid query, deducting one request
def run_paid_query(user_id):
    payload = {"user_id": user_id}
    response = requests.post(f"{BASE_URL}/run_paid_query", json=payload)
    if response.status_code == 200:
        result = response.json()
        st.success(f"Query executed!")
        st.write(f"Query result: {result['result']}")
    else:
        st.error(response.json().get("error", "Insufficient request balance."))


# Streamlit UI elements
st.title("User Request Management")

# Fetch users and allow selection
users = get_all_users()
user_names = [user["name"] for user in users]
selected_user_name = st.selectbox("Select a user", user_names)

# Get selected user ID
selected_user = next(user for user in users if user["name"] == selected_user_name)

# Show user's request balance
st.subheader(f"Request Balance for {selected_user_name}")
balance_container = st.empty()
balance = get_user_balance(selected_user["id"])
balance_container.write(f"Available Requests: {balance}")

# Section for running a paid query
st.subheader("Run Paid Query")
if st.button("Run Query"):
    run_paid_query(selected_user["id"])
    balance = get_user_balance(
        selected_user["id"]
    )  # Fetch new balance after running the paid query
    balance_container.write(f"Available Requests: {balance}")

# Section for purchasing requests
st.subheader("Purchase More Requests")
purchase_amount = st.number_input(
    "How many requests would you like to buy?", min_value=10, step=10
)

if st.button("Check Balance"):
    # Call backend to calculate AGIX needed
    payload = {"user_id": selected_user["id"], "num_requests": purchase_amount}
    response = requests.post(f"{BASE_URL}/purchase_requests", json=payload)

    if response.status_code == 200:
        data = response.json()
        st.write(f"AGIX Balance: {data['agix_balance']} AGIX")
        st.write(
            f"Required AGIX for {purchase_amount} requests: {data['required_agix']} AGIX"
        )
        st.write(f"Remaining AGIX after purchase: {data['remaining_agix']} AGIX")
        st.session_state.confirm_button = True
        st.session_state.required_agix = data['required_agix']

if "confirm_button" not in st.session_state:
    st.session_state.confirm_button = False

if st.session_state.confirm_button:
    if st.button("Confirm Purchase"):
        # Call confirm_purchase endpoint to execute AGIX transfer
        confirm_payload = {
            "user_id": selected_user["id"],
            "amount_agix": st.session_state.required_agix,
        }
        confirm_response = requests.post(
            f"{BASE_URL}/confirm_purchase", json=confirm_payload
        )
        if confirm_response.status_code == 200:
            tx_data = confirm_response.json()
            st.success(
                f"Transaction successful! Hash: {tx_data['transaction_hash']}"
            )
            st.success(f"link: https://sepolia.etherscan.io/tx/0x{tx_data['transaction_hash']}")
            balance = get_user_balance(
                selected_user["id"]
            )  # Fetch new balance after running the paid query
            balance_container.write(f"Available Requests: {balance}")
        else:
            st.error("Transaction failed!")
