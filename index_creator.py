from azure.search.documents.indexes.models import SearchIndex, SearchableField, SimpleField
from azure.core.exceptions import ResourceNotFoundError

def create_search_index(index_client,index_name):

    # Define fields for the index
    fields = [
        SimpleField(name="id", type="Edm.String", key=True),  # Unique key
        SearchableField(name="name", type="Edm.String"),  # Name
        SearchableField(name="email", type="Edm.String"),  # Email
        SearchableField(name="city", type="Edm.String"),  # City
        SearchableField(name="skills", type="Edm.String"),  # Skills
        SearchableField(name="role", type="Edm.String"),  # Role
        SearchableField(name="phonenumber", type="Edm.String"), # Phone Number
        SearchableField(name="filename", type="Edm.String"),  # Phone Number
        SearchableField(name="resume_url", type="Edm.String") # Blob_URL
    ]

    # Define the index
    index = SearchIndex(name=index_name, fields=fields)

    try:
        # Check if the index already exists
        index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except ResourceNotFoundError:
        # If the index doesn't exist, create it
        index_client.create_index(index)
        print(f"Index '{index_name}' created successfully!")


if __name__ == '__main__':
    create_search_index()
