import base64

def analyze_resume(form_recognizer_client,blob_url,filename):

    try:
        # Call Form Recognizer on the Blob URL (using prebuilt-resume model)
        poller = form_recognizer_client.begin_analyze_document_from_url(
            "resume-extractor-v2", blob_url
        )

        # Wait for the result and get the analyzed document
        result = poller.result()

        extracted_data = {}
        for document in result.documents:
            for field, field_value in document.fields.items():
                extracted_data[field] = field_value.content if field_value.content else 'No value'
                #add blob file url and file name as well to the dictionary
                extracted_data['filename'] = filename
                extracted_data['resume_url'] = blob_url

    except Exception as e:
        print(f'Error during resume analysis: {e}')
        return {"error": str(e)}

    #print(extracted_data)
    return extracted_data

# Function to upload the extracted data to the Azure Cognitive Search index
def upload_to_search_index(extracted_data, filename,search_client):

    # Format the document for Azure Search
    safe_filename = base64.urlsafe_b64encode(filename.encode()).decode().strip("=")
    document = {
        "id": safe_filename,  # Use the filename as a unique identifier
        "name": extracted_data.get("name", "N/A"),
        "email": extracted_data.get("email", "N/A"),
        "city": extracted_data.get("city", "N/A"),
        "skills": extracted_data.get("skill", "N/A"),
        "role": extracted_data.get("role", "N/A"),
        "phonenumber": extracted_data.get("phonenumber", "N/A"),
        "filename": extracted_data.get("filename", "N/A"),
        "resume_url": extracted_data.get("resume_url", "N/A")
    }

    #Upload document to the search index
    result = search_client.upload_documents(documents=[document])

    if result[0].succeeded:
        print(f"Document for {filename} uploaded successfully!")
    else:
        print(f"Failed to upload document for {filename}")


def search_in_index(query,search_client):
    """Searches indexed resumes in Azure AI Search."""
    results = search_client.search(
        search_text=query,
        top=10  # Limit results
    )

    extracted_results = []
    for result in results:
        extracted_results.append({
            "name": result["name"],
            "skills": result["skills"],
            "role": result["role"],
            "filename": result["filename"],
            "resume_url": result["resume_url"]
        })

    return extracted_results
    #print(extracted_results)
