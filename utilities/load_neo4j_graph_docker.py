import zipfile
import io
import json, asyncio
from py2neo import Graph
import os, sys

sys.path.append(os.path.join(sys.path[0], ".."))
from utilities import hash_utilities,neo4j_utilities

import logging       
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_query_with_retry(graph_server, query, package, max_retries=20):
    attempt = 0
    while attempt < max_retries:
        try:
           
            await neo4j_utilities.run_query_async(graph_server, query, package)
            break  #
        except Exception as e:
            print(f"Error executing the request: {e}, attempt {attempt + 1}/{max_retries}")
            attempt += 1
            if attempt == max_retries:
                print("The maximum number of attempts has been reached, the task will be aborted.")
                raise
            await asyncio.sleep(1*attempt) 


def create_nodes(graph_server:Graph, list_of_autors:list,list_of_doi:list):
    print("")  # Print a newline for separation or debugging purposes.

    # Create a node in the graph for each DOI.
    list_nodes_to_insert= []
    query = "CREATE INDEX author_index_1 FOR (n:author) ON (n.id_hash)"
    try:

        graph_server.run(query)
    except:
        print("index not create")
    for author in list_of_autors:
        
        list_nodes_to_insert.append(author)
    query = """
        UNWIND $nodes AS props
        MERGE (n:author{id_hash: props.id_hash})
        SET n += props
        """
    

    chunk_size = 10000
    packages = [list(list_nodes_to_insert[i:i + chunk_size]) for i in range(0, len(list_nodes_to_insert), chunk_size)]
    for pack in packages:
        graph_server.run(query, nodes=pack)
    

    list_nodes_to_insert = []
    query = "CREATE INDEX doi_index_1 FOR (n:doi) ON (n.name)"
    try:

        graph_server.run(query)
    except:
        print("index not create")
    for doi in list_of_doi:
        # node ={"name":doi.split(".json")[0]}
        # Create a new node with label 'doi' and its name set to the DOI.
        list_nodes_to_insert.append(doi)
    query = """
        UNWIND $nodes AS props
        MERGE (n:doi{name: props.name})
        SET n += props
        """
    
   
    chunk_size = 10000
    packages = [list(list_nodes_to_insert[i:i + chunk_size]) for i in range(0, len(list_nodes_to_insert), chunk_size)]
    for pack in packages:
        graph_server.run(query, nodes=pack)
   
    


async def create_relations(graph_server:Graph, zip_content):
    relation_list_to_insert_ref = []
    relation_list_to_insert_author = []
    # Iterate over the DOIs to create relationships based on the JSON data.
    print("create list of rel")

    # Modify the DOI to match the filename format.
    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        for file_info in z.infolist():
            with z.open(file_info) as file:
                json_data = json.load(file)
                
                doi = ""   
                if "id" in json_data:
                        if "dois" in json_data["id"]:
                            doi = json_data["id"]["dois"][0]
                # Check if the JSON data includes references.
                if doi:
                    if "references" in json_data:
                        # Iterate through each reference.
                        for ref in json_data["references"]:
                            # Create a new dictionary for each relationship to prevent overwriting
                            relationship = {
                                "start": doi,
                                "type": "reference",
                                "end": ref["doi"]
                            }
                        
                            relation_list_to_insert_ref.append(relationship)
                    if "authors" in json_data:
                        for author in json_data["authors"]:
                            author_name = hash_utilities.stable_json_hash(author)
                            relationship = {
                                "start": author_name,
                                "type": "author",
                                "end": doi
                            }
                        
                            relation_list_to_insert_author.append(relationship)
                    

        print(f"""count author rel {len(relation_list_to_insert_author)}
    count ref rel {len(relation_list_to_insert_ref)}
    """)
                    
        query = """
                UNWIND $relationships as rel
                MATCH (start:doi {name: rel.start}), (end:doi {name: rel.end})
                MERGE (start)-[:reference]->(end)
                """
        packages = []
        chunk_size = 100
        packages = [list(relation_list_to_insert_ref[i:i + chunk_size]) for i in range(0, len(relation_list_to_insert_ref), chunk_size)]
        i = 0
        print("reference")
    
        tasks = []
        for i, package in enumerate(packages):
            # print(i)
            # Creating a task for each package.
            task = asyncio.create_task(run_query_with_retry(graph_server, query, package))
            tasks.append(task)
            # Deleting completed tasks from the list to free up memory.
            tasks = [t for t in tasks if not t.done()]

            # Checking and waiting if the limit of concurrent tasks is reached.
            if len(tasks) >= 20:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    
            # print(f"Execution time: {elapsed_time} seconds. {i}    {len(packages)}")

        await asyncio.gather(*tasks)
    



        packages = []
        packages = [list(relation_list_to_insert_author[i:i + chunk_size]) for i in range(0, len(relation_list_to_insert_author), chunk_size)]
        query = """
                UNWIND $relationships as rel
                MATCH (start:author {id_hash: rel.start}), (end:doi {name: rel.end})
                MERGE (start)-[:author]->(end)
                MERGE (end)-[:author]->(start)
                """
        i = 0
        print("author")
        # start_time = time.time()
        tasks = []
        for i, package in enumerate(packages):
            # print(i)
        
            task = asyncio.create_task(run_query_with_retry(graph_server, query, package))
            tasks.append(task)
        
            tasks = [t for t in tasks if not t.done()]

            if len(tasks) >= 20:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    
            # print(f"Execution time: {elapsed_time} seconds. {i}    {len(packages)}")

        await asyncio.gather(*tasks)
        return len(relation_list_to_insert_ref)+len(relation_list_to_insert_author)




async def process_zip_in_memory(zip_content):
    list_of_doi = []
    list_of_autors = []

    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        for file_info in z.infolist():
            with z.open(file_info) as file:
                data = json.load(file)
                if "id" in data:
                    if "dois" in data["id"]:
                        doi = {"name":data["id"]["dois"][0]}
                        if "abstract" in data:
                            doi["abstract"] = data["abstract"]
                        if "title" in data:
                            doi["title"] = data["title"]
                        if "issued_at" in data:
                            doi["issued_at"] = data["issued_at"]
                        if "languages" in data:
                            doi["languages"] = data["languages"]
                        
                        if "tags" in data:
                            doi["tags"] = data["tags"]
                        if "metadata" in data:
                            if "container_title" in data["metadata"]:
                                doi["container_title"] = data["metadata"]["container_title"]
                            if "iso_id" in data["metadata"]:
                                doi["iso_id"] = data["metadata"]["iso_id"]

                            if "isbns" in data["metadata"]:
                                doi["isbns"] = data["metadata"]["isbns"]

                        if "links" in data:
                            if "cid" in data["links"]:
                                doi["cid"] = data["links"]["cid"]
                        if "type" in data:
                            doi["type"] = data["type"]
                        if "updated_at" in data:
                            doi["updated_at"] = data["updated_at"]
                        
                        
                        if "internal_iso" in data["id"]:
                            doi["internal_iso"] = data["id"]["internal_iso"]
                        if "libgen_ids" in data["id"]:
                            doi["libgen_ids"] = data["id"]["libgen_ids"]
                        if "zlibrary_ids" in data["id"]:
                            doi["zlibrary_ids"] = data["id"]["zlibrary_ids"]
                        if "content" in data:
                            doi["is_content_present"] = True
                        else:
                            doi["is_content_present"] = False
                        list_of_doi.append(doi)
                if "references" in data:
                    for ref in data["references"]:
                        list_of_doi.append({"name": ref["doi"]})
                if "authors" in data:
                    for author in data["authors"]:
                        author_insert = {"id_hash": hash_utilities.stable_json_hash(data=author)}
                        if "family" in author:
                            author_insert["family"] = author["family"]
                        if "given" in author:
                            author_insert["given"] = author["given"]
                        if "orcid" in author:
                            author_insert["orcid"] = author['orcid']
                        list_of_autors.append(author_insert)

        DATABASE_NAME = "smallstc"     
        graph_server = neo4j_utilities.wrapper_connection_to_neo4j_database(
        DATABASE_NAME=DATABASE_NAME,
    
      
    )
        create_nodes(graph_server=graph_server,list_of_autors=list_of_autors,list_of_doi=list_of_doi)
        count_nodes = len(list_of_doi)+len(list_of_autors)
        # with open("/home/daniil/project/kg_snet_vbrl/logs/stc_to_neo.log/timing_new.log", "a") as log_file:
        #     log_file.write(f"{path_dir}   count of nodes: {count_nodes}   create nodes : {time.time()-start_time_node} seconds    performance: {count_nodes/(finish_time_node-start_time_node)} count/s\n")
        list_of_doi,list_of_autors = [],[]
        list_of_file_for_rel = []
        count_rel = await create_relations(graph_server=graph_server,zip_content=zip_content)

    
        # with open("/home/daniil/project/kg_snet_vbrl/logs/stc_to_neo.log/timing_new.log", "a") as log_file:
        #     log_file.write(f"{path_dir}  count of reletions: {count_rel}   insert relations : {time.time()-start_time_rel} seconds    performance: {count_rel/(finish_time_rel-start_time_rel)}\n")
        list_of_file_for_rel = []
        
        # with open("/home/daniil/project/kg_snet_vbrl/logs/stc_to_neo.log/timing_new.log", "a") as log_file:
        #     log_file.write(f"{path_dir}     total time : {time.time()-start_total_time} seconds\n")
              
   
            



def unzip_file():
    zip_file_path = 'data/stc_data_2_ms.zip'

    with open(zip_file_path, 'rb') as f:
        zip_content = f.read()

    asyncio.run(process_zip_in_memory(zip_content))
    logger.info("finish upload data to graph")


import time
if __name__ == "__main__":
    time.sleep(60)
    unzip_file()
