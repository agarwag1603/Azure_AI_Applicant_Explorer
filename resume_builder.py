from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv
import process_resume
import index_creator
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from flask import Flask, request, redirect, url_for, render_template
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI


# Load environment variables
load_dotenv()
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_SECRET_ID = os.getenv("AZURE_SECRET_ID")


#Key vault name and url
KEY_VAULT_NAME = "resume-explorer-keys"
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

# Authenticate using ClientSecretCredential
_credential = ClientSecretCredential(
    tenant_id=AZURE_TENANT_ID,
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_SECRET_ID
)

secret_client = SecretClient(vault_url=KV_URI, credential=_credential)

#fetch all the key vault secrets
SEARCH_ENDPOINT=secret_client.get_secret('SEARCHENDPOINT').value
SEARCH_API_KEY=secret_client.get_secret('SEARCHAPIKEY').value
FORM_RECOGNIZER_ENDPOINT=secret_client.get_secret('FORMRECOGNIZERENDPOINT').value
FORM_RECOGNIZER_KEY=secret_client.get_secret('FORMRECOGNIZERKEY').value
STORAGE_ACCOUNT_KEY=secret_client.get_secret('STORAGEACCOUNTKEY').value
OPENAI_ENDPOINT_URL=secret_client.get_secret('OPENAIENDPOINTURL').value
OPENAI_KEY=secret_client.get_secret('OPENAIKEY').value


# Azure Storage Config
STORAGE_ACCOUNT_NAME = 'resumelander'
CONTAINER_NAME = 'resumedata'
CONTAINER_SAS_TOKEN=''

#AI Search config
INDEX_NAME = "resume-index-2"

#Azure Open AI config
OPENAI_DEPLOYMENT = "gpt-4o-resume-explorer"

#Blob container interface
blob_service_client = BlobServiceClient(
    f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=STORAGE_ACCOUNT_KEY
)
#Document intelligence interface
form_recognizer_client = DocumentAnalysisClient(
        endpoint=FORM_RECOGNIZER_ENDPOINT,
        credential=AzureKeyCredential(FORM_RECOGNIZER_KEY)
    )

#AI search interface
search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_API_KEY)
    )

#Search Index  interface
index_client = SearchIndexClient(
    endpoint=SEARCH_ENDPOINT,
    credential=AzureKeyCredential(SEARCH_API_KEY)
    )

client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT_URL,
    api_key=OPENAI_KEY,
    api_version="2024-05-01-preview",
)

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')  # Get all files uploaded

    for file in files:
        if file:
            # Create a blob client for each file
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file.filename)

            # Upload the file to Azure Blob Storage
            blob_client.upload_blob(file, overwrite=True)

            # Get the Blob URL for the file you uploaded
            blob_url = blob_client.url
            blob_url = f"{blob_url}?{CONTAINER_SAS_TOKEN}"
            # print(blob_url)

            # Create index by calling index_creator.py
            index_creator.create_search_index(index_client, INDEX_NAME)

            extracted_data = process_resume.analyze_resume(form_recognizer_client,blob_url,file.filename)
            #print(extracted_data)

            process_resume.upload_to_search_index(extracted_data, file.filename,search_client)

            #return jsonify({
            #    "message": f"File {file.filename} uploaded successfully! Redirecting to home page!"
            #})

            return redirect(url_for('index'))  # Redirect back to the homepage after upload

#@app.route("/search", methods=["GET"])
# def search():
#     query = request.args.get("query", "").strip()
#     search_results = None
#
#     if query:
#         search_results = process_resume.search_in_index(query,search_client)
#         print(f"Search results: {search_results}")
#     return render_template("search_results.html", search_results=search_results)

from flask import jsonify

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").strip()
    search_results = None

    if query:
        search_results = process_resume.search_in_index(query,search_client)

    # Return JSON
    return jsonify({"search_results": search_results})  # Return a JSON object


@app.route('/chat', methods=['POST'])
def chat():
    if request.method == "POST":
        user_input = request.json.get("user_input", "").strip()  # Updated to handle JSON data
        if not user_input:
            return jsonify({"error": "No input provided"}), 400

        messages = [
            {"role": "system", "content": "You are an AI assistant that helps only with applicants exploration."},
            {"role": "user", "content": user_input}
        ]

        completion = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": SEARCH_ENDPOINT,
                        "index_name": INDEX_NAME,
                        "semantic_configuration": "semantic-config",
                        "query_type": "semantic",
                        "role_information": "You are an AI assistant that helps HR recruiters with applicant information.",
                        "strictness": 3,
                        "top_n_documents": 5,
                        "authentication": {"type": "api_key", "key": SEARCH_API_KEY}
                    }
                }]
            }
        )

        response = completion.choices[0].message.content
        return jsonify({"response": response})  # Return JSON response
        #return jsonify({"response": answer})


@app.route('/')
def index():
    return render_template('upload_search.html')


if __name__ == '__main__':
    app.run(debug=True)