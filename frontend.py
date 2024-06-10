import streamlit as st
import requests

# Ensure this is called before any other Streamlit functions
#st.set_page_config(layout="wide")

# Page layout
tab1, tab2 = st.tabs(["Chat", "Settings"])

# Sidebar for session management
st.sidebar.title("Sessions")
response = requests.get("http://127.0.0.1:8000/sessions")
if response.status_code == 200:
    sessions = response.json()["sessions"]
else:
    sessions = []

if 'selected_session' not in st.session_state:
    st.session_state['selected_session'] = ""

if st.sidebar.button("Start New Session"):
    response = requests.post("http://127.0.0.1:8000/sessions")
    if response.status_code == 200:
        new_session = response.json()["session_id"]
        st.session_state['selected_session'] = new_session
        st.sidebar.success("New session started")
        st.experimental_rerun()
    else:
        st.sidebar.error("Error starting new session")

selected_session = st.sidebar.selectbox("Select Session", sessions, index=sessions.index(st.session_state['selected_session']) if st.session_state['selected_session'] in sessions else 0)

with tab1:
    st.header("Chatbot Interface with Neo4j Integration")

    if selected_session:
        user_input = st.text_input("Type question:", "")

        if st.button("Ask"):
            if user_input:
                response = requests.post("http://127.0.0.1:8000/chat", json={"message": user_input, "session_id": selected_session})
                if response.status_code == 200:
                    bot_response = response.json()["response"]
                    st.text_area("Bot:", value=bot_response, height=100)
                else:
                    st.error("Error from backend")
    else:
        st.text("Please select a session to start chatting.")

    # Space for graph visualization
    if selected_session:
        st.subheader("Graph Visualization")
        graph_data = requests.get(f"http://127.0.0.1:8000/graph?session_id={selected_session}")
        if graph_data.status_code == 200:
            st.graphviz_chart(graph_data.json()["graph"])
        else:
            st.error("Error fetching graph data")

with tab2:
    st.header("Settings")

    with st.expander("Neo4j Connection"):
        neo4j_uri = st.text_input("URI", "")
        neo4j_username = st.text_input("Username", "")
        neo4j_password = st.text_input("Password", type="password")
        neo4j_database = st.text_input("Database", "")

    with st.expander("Neo4j Graph Visualization"):
        initial_node_display = st.text_input("Initial Node Display", "")
        max_neighbours = st.number_input("Max Neighbours", min_value=1, value=10)
        max_rows = st.number_input("Max Rows", min_value=1, value=100)

    with st.expander("LLM Settings"):
        cloud_provider = st.text_input("Cloud Provider", "")
        api_key = st.text_input("API Key", "")
        server = st.text_input("Server", "")

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
            "server": server
        }
        response = requests.post("http://127.0.0.1:8000/configure_neo4j", json=settings)
        if response.status_code == 200:
            st.success("Settings saved")
        else:
            st.error("Error saving settings")
