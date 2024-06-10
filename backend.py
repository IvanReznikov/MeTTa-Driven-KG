from fastapi import FastAPI
from pydantic import BaseModel
from neo4j import GraphDatabase
from uuid import uuid4
import json
import os

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str

class Neo4jConfig(BaseModel):
    uri: str
    username: str
    password: str
    database: str

SESSION_FILE = "sessions.json"
sessions = {}
neo4j_driver = None
neo4j_database = None

def load_sessions():
    global sessions
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            sessions = json.load(f)

def save_sessions():
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f)

load_sessions()

@app.post("/configure_neo4j")
def configure_neo4j(config: Neo4jConfig):
    global neo4j_driver, neo4j_database
    neo4j_driver = GraphDatabase.driver(config.uri, auth=(config.username, config.password))
    neo4j_database = config.database
    return {"status": "Neo4j configuration successful"}

@app.post("/sessions")
def start_new_session():
    session_id = str(uuid4())
    sessions[session_id] = {"messages": []}
    save_sessions()
    return {"session_id": session_id}

@app.get("/sessions")
def get_sessions():
    return {"sessions": list(sessions.keys())}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message
    session_id = chat_request.session_id

    if session_id not in sessions:
        return {"response": "Session not found"}

    sessions[session_id]["messages"].append(user_message)
    save_sessions()
    # Simple echo response for testing
    chatbot_response = f"Echo: {user_message}"
    return ChatResponse(response=chatbot_response)

@app.get("/graph")
def get_graph(session_id: str):
    if session_id not in sessions:
        return {"graph": ""}
    
    with neo4j_driver.session(database=neo4j_database) as session:
        result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25")
        nodes = []
        edges = []
        for record in result:
            nodes.append(record["n"])
            nodes.append(record["m"])
            edges.append(record["r"])
        nodes = list({str(node.id): node for node in nodes}.values())
        nodes_str = " ".join([f'"{node.id}" [label="{node.labels[0]}"]' for node in nodes])
        edges_str = " ".join([f'"{edge.start_node.id}" -> "{edge.end_node.id}" [label="{edge.type}"]' for edge in edges])
        graph_str = f'digraph G {{ {nodes_str} {edges_str} }}'
    return {"graph": graph_str}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
