## Milestone 2 - Integration Of KGs & LLMs

### Description
This milestone focuses on integrating Large Language Models (LLMs) for preprocessing data from the STC graph and enabling natural language query capabilities. The goal is to enhance the STC graph with more accurate data and provide a system where users can query the graph using natural language.

### Deliverables
- An LLM-integrated system with natural language query functionality.

### Progress Made

#### Data Folder
The data folder contains a small portion of the STC graph. To run Neo4j on this data, use the following instructions:
1. config .env files same/similar to .env.example

2. run container with Neo4j
```bash
docker compose up
```

3. The `smallstc` graph will be build dynamically - just wait a couple of minutes. Afterwards, you'll be able to run the graph without delay.

#### Preprocessing Articles' Language
We used an LLM to identify the languages of articles based on their titles, filling in missing language values. This preprocessing step ensures that the language data in the graph is accurate and complete.

#### Creating an Anthology for Tags
An LLM was employed to create an anthology for tags mentioned in the articles. This resulted in a better understanding of the authors' fields of study and the topics of the articles. The hierarchical structure of tags enhances the semantic richness of the graph.

#### Resolving Author Mismatches
We used embedding models to resolve mismatches between authors with similar names (e.g., John Doe, Jason Doe, and J. Doe). By comparing the titles of their published articles and analyzing similarity scores, we identified, for example, that "J. Doe" is indeed "Jason Doe."

#### Natural Language Query Capabilities
We demonstrated the potential of LangChain's `GraphCypherQAChain` to allow users to ask the graph questions in natural language. This was achieved by implementing few-shot examples to train the system on how to interpret and convert natural language queries into Cypher statements for Neo4j.

### Conclusion
In this milestone, we have successfully integrated LLMs to preprocess data, create a hierarchical structure for tags, resolve author mismatches, and enable natural language queries for the STC graph. These advancements have significantly improved the accuracy and usability of the STC graph, providing a powerful tool for querying and analyzing the data.