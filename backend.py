from fastapi import FastAPI
from pydantic import BaseModel
from neo4j import GraphDatabase
from uuid import uuid4
import json
import os
from dotenv import load_dotenv
from pyvis.network import Network

from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI

import uvicorn
from itertools import cycle

load_dotenv()

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
langchain_graph = None


def load_sessions():
    global sessions
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            sessions = json.load(f)


def save_sessions():
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f)


def initialize_neo4j():
    global neo4j_driver, neo4j_database, langchain_graph
    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_username = os.getenv("NEO4J_USERNAME", "")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database = os.getenv("NEO4J_DATABASE", "")
    if neo4j_uri and neo4j_username and neo4j_password:
        neo4j_driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_username, neo4j_password)
        )
        neo4j_database = neo4j_database
    try:
        langchain_graph = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database,
        )
    except Exception as e:
        print(e)


def set_model():
    return ChatOpenAI(
        model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY", ""), temperature=0
    )


model = set_model()


def paraphrase_question_viz(query):
    prompt = ChatPromptTemplate.from_template(
        """
    You need to modify user query.
    Replace the count statement with the who or what and return list.
                                              
    Examples:
    Query: How many articles reference "abc/123"?
    Response: What articles reference "abc/123"?
                                              
    Query: How many coautors John Doe has?
    Response: Who are the coauthors of John Doe? 

    Query: How many articles were authored by John Doe?
    Response: What articles were authored by John Doe?

    Query: {query}
    """
    )
    output_parser = StrOutputParser()

    chain = prompt | model | output_parser

    return chain.invoke({"query": query})


def run_query_langchain_graph_chain():
    CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.
    Schema:
    {schema}
    Note: Do not include any explanations or apologies in your responses.
    Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
    Do not include any text except the generated Cypher statement.
    Examples: Here are a few examples of generated Cypher statements for particular questions:
    # List the titles of articles written by John Doe.
    MATCH (a:author {{given: "John", family: "Doe"}})<-[:author]-(art:article)
    RETURN art.title

    # What articles reference the article 10.1177/1049732311417455?
    MATCH (d:doi {{name: "10.1177/1049732311417455"}})-[:reference]->(ref:doi)
    RETURN ref.name as source_name, d.name as target_name

    # What articles the article 10.1177/1049732311417455 references?
    MATCH (d:doi {{name: "10.1177/1049732311417455"}})<-[:reference]-(ref:doi)
    RETURN d.name as source_name, ref.name as target_name

    The question is:
    {question}"""

    CYPHER_GENERATION_PROMPT = PromptTemplate(
        input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
    )

    chain = GraphCypherQAChain.from_llm(
        model,
        graph=langchain_graph,
        verbose=True,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        validate_cypher=True,
        top_k=100,
    )

    return chain


def run_viz_langchain_graph_chain():
    CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
    Instructions:
    Use only the provided relationship types and properties in the schema.
    Do not use any other relationship types or properties that are not provided.
    Schema:
    {schema}
  
    It is important to provide source_ and target_ prefixes!
    Don't use COUNT!!! List all results

    # Query to retrieve all coauthors of John Doe:
    MATCH (a:author {{family: "Doe", given: "John"}})-[:author]-(article:article)-[:author]-(coauthor:author)
    WHERE NOT (coauthor.family = "Doe" AND coauthor.given = "John")
    RETURN coauthor.family AS source_family, coauthor.given AS source_given, article.name as target_name

    # What articles are authored by John Doe:
    MATCH (a:author {{family: "Doe", given: "John"}})-[:author]->(article:article)
    RETURN author.family AS source_family, author.given AS source_given, article.name as target_name

    # What authors does the 10.1177/1049732311417455 have?
    MATCH (d:doi {{name: "10.1177/1049732311417455"}})-[:author]->(a:author)
    RETURN d.name as source_name, author.family AS target_family, author.given AS target_given, 

    # What articles reference the article 10.1177/1049732311417455?
    MATCH (d:doi {{name: "10.1177/1049732311417455"}})-[:reference]->(ref:doi)
    RETURN ref.name as source_name, d.name as target_name

    # What articles the article 10.1177/1049732311417455 references?
    MATCH (d:doi {{name: "10.1177/1049732311417455"}})<-[:reference]-(ref:doi)
    RETURN d.name as source_name, ref.name as target_name

    The question is:
    {question}"""

    CYPHER_GENERATION_PROMPT = PromptTemplate(
        input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
    )

    chain = GraphCypherQAChain.from_llm(
        model,
        graph=langchain_graph,
        verbose=True,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        validate_cypher=True,
        return_direct=True,
        top_k=100,
    )

    return chain


initialize_neo4j()
load_sessions()
langchain_graph_chain = run_query_langchain_graph_chain()
langchain_graph_viz_chain = run_viz_langchain_graph_chain()


@app.post("/configure_neo4j")
def configure_neo4j(config: Neo4jConfig):
    global neo4j_driver, neo4j_database
    neo4j_driver = GraphDatabase.driver(
        config.uri, auth=(config.username, config.password)
    )
    neo4j_database = config.database
    settings = {
        "NEO4J_URI": config.uri,
        "NEO4J_USERNAME": config.username,
        "NEO4J_PASSWORD": config.password,
        "NEO4J_DATABASE": config.database,
    }
    with open(SESSION_FILE, "r+") as f:
        data = json.load(f)
        data["settings"] = settings
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
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
    chatbot_response = langchain_graph_chain.run(user_message)
    return ChatResponse(response=chatbot_response)


def create_network_graph(
    data,
    node_size=20,
    node_colors=None,
    edge_color="#484848",
):
    net = Network(
        height="750px",
        width="100%",
        notebook=True,
        directed=True,
        bgcolor="#DBDBDB",
        font_color="#000000",
    )

    # Default color palette if none provided
    if node_colors is None:
        node_colors = [
            "#4508DF",
            "#0878E0",
            "#BD0CDF",
            "#820CDF",
            "#5E3DFF",
            "#3083DC",
            "#9627BA",
            "#D885FF",
            "#6900CE",
            "#A15BFF",
            "#6E00FC",
            "#009BDF",
            "#B362F8",
            "#7730F9",
            "#3A82F7",
            "#A850E7",
            "#429BF5",
            "#8E72FA",
            "#2E61F8",
            "#BF6DF6",
        ]

    # List of colors to cycle through
    colors = cycle(node_colors)
    color_map = {}  # This will map node labels to colors

    print(data)

    for record in data:
        for node in record:
            if "source_" in node:
                source = record[node]
                source_key = node.replace("source_", "")
            if "target_" in node:
                target = record[node]
                target_key = node.replace("target_", "")

        if source_key == "given" or source_key == "family":
            relationship = "authored"

        elif target_key == "given" or target_key == "family":
            relationship = "authored_by"

        else:
            relationship = "reference"

        # Assign color to source node if it's not already assigned
        if source not in color_map:
            color_map[source] = next(colors)

        # Assign color to target node if it's not already assigned
        if target not in color_map:
            color_map[target] = next(colors)

        net.add_node(
            source, label=source, color=color_map[source], size=node_size, title=source
        )
        net.add_node(
            target, label=target, color=color_map[target], size=node_size, title=target
        )
        net.add_edge(
            source,
            target,
            label=relationship,
            color=edge_color,
            width=2,
            arrowStrikethrough=True,
            dashes=True,
            font={"align": "horizontal", "color": "black"},
        )

    return net


def display_network_graph(net, file_path="graph.html"):
    net.repulsion(node_distance=300)
    net.show_buttons()
    net.show(file_path)
    return file_path


@app.post("/graph")
def get_graph(chat_request: ChatRequest):
    user_message = chat_request.message
    query = paraphrase_question_viz(user_message)
    result = langchain_graph_viz_chain.run(query)
    net = create_network_graph(result)
    return display_network_graph(net)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
