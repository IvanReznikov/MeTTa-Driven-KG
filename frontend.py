import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import json

# Ensure this is called before any other Streamlit functions
st.set_page_config(layout="wide")

# Load settings from session file and environment variables
SESSION_FILE = "sessions.json"
settings = {
    "neo4j_uri": os.getenv("NEO4J_URI", ""),
    "neo4j_username": os.getenv("NEO4J_USERNAME", ""),
    "neo4j_password": os.getenv("NEO4J_PASSWORD", ""),
    "neo4j_database": os.getenv("NEO4J_DATABASE", ""),
    "initial_node_display": os.getenv("INITIAL_NODE_DISPLAY", ""),
    "max_neighbours": os.getenv("MAX_NEIGHBOURS", 100),
    "max_rows": os.getenv("MAX_ROWS", 100),
    "cloud_provider": os.getenv("CLOUD_PROVIDER", ""),
    "api_key": os.getenv("API_KEY", ""),
    "server": os.getenv("SERVER", ""),
}

if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        sessions_data = json.load(f)
        if "settings" in sessions_data:
            settings.update(sessions_data["settings"])

# Page layout
tab1, tab2 = st.tabs(["Chat", "Settings"])

# Sidebar for session management
st.sidebar.title("Sessions")
response = requests.get("http://127.0.0.1:8000/sessions")
if response.status_code == 200:
    sessions = response.json()["sessions"]
else:
    sessions = []

if "selected_session" not in st.session_state:
    st.session_state["selected_session"] = ""

if st.sidebar.button("Start New Session"):
    response = requests.post("http://127.0.0.1:8000/sessions")
    if response.status_code == 200:
        new_session = response.json()["session_id"]
        st.session_state["selected_session"] = new_session
        st.sidebar.success("New session started")
        st.experimental_rerun()
    else:
        st.sidebar.error("Error starting new session")

selected_session = st.sidebar.selectbox(
    "Select Session",
    sessions,
    index=sessions.index(st.session_state["selected_session"])
    if st.session_state["selected_session"] in sessions
    else 0,
)

with tab1:
    st.header("Chatbot Interface with Neo4j Integration")

    if selected_session:
        user_input = st.text_input("Type question:", "")

        if st.button("Ask"):
            if user_input:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={"message": user_input, "session_id": selected_session},
                )
                if response.status_code == 200:
                    bot_response = response.json()["response"]
                    st.text_area("Bot:", value=bot_response, height=100)
                    st.session_state["asked_question"] = True
                else:
                    st.error("Error from backend")

        else:
            st.text("Please select a session to start chatting.")

        # Space for graph visualization
        if selected_session and st.session_state.get("asked_question", False):
            st.subheader("Graph Visualization")
            graph_data = requests.post(
                "http://127.0.0.1:8000/graph",
                json={"message": user_input, "session_id": selected_session},
            )
            if graph_data.status_code == 200:
                HtmlFile = open(graph_data.json(), "r", encoding="utf-8")
                source_code = HtmlFile.read()
                components.html(source_code, height=750)
            else:
                st.error("Error fetching graph data")

with tab2:
    st.header("Settings")

    with st.expander("Neo4j Connection"):
        neo4j_uri = st.text_input("URI", value=settings["neo4j_uri"])
        neo4j_username = st.text_input("Username", value=settings["neo4j_username"])
        neo4j_password = st.text_input(
            "Password", type="password", value=settings["neo4j_password"]
        )
        neo4j_database = st.text_input("Database", value=settings["neo4j_database"])

    with st.expander("Neo4j Graph Visualization"):
        initial_node_display = st.text_input(
            "Initial Node Display", value=settings["initial_node_display"]
        )
        max_neighbours = st.number_input(
            "Max Neighbours", min_value=1, value=int(settings["max_neighbours"])
        )
        max_rows = st.number_input(
            "Max Rows", min_value=1, value=int(settings["max_rows"])
        )

    with st.expander("LLM Settings"):
        cloud_provider = st.text_input(
            "Cloud Provider", value=settings["cloud_provider"]
        )
        api_key = st.text_input("API Key", value=settings["api_key"])
        server = st.text_input("Server", value=settings["server"])

    if st.button("Save Settings"):
        settings = {
            "neo4j_uri": neo4j_uri,
            "neo4j_username": neo4j_username,
            "neo4j_password": neo4j_password,
            "neo4j_database": neo4j_database,
            "initial_node_display": initial_node_display,
            "max_neighbours": max_neighbours,
            "max_rows": max_rows,
            "cloud_provider": cloud_provider,
            "api_key": api_key,
            "server": server,
        }
        response = requests.post("http://127.0.0.1:8000/configure_neo4j", json=settings)
        if response.status_code == 200:
            st.success("Settings saved")
            # Save settings to the session file
            with open(SESSION_FILE, "r+") as f:
                data = json.load(f)
                data["settings"] = settings
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
        else:
            st.error("Error saving settings")
