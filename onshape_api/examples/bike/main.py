import onshape_api

client = onshape_api.Client(env="/Users/holycow/Projects/onshape-api/.env")
print(client.list_documents().json())

# new_doc = c.new_document(name="Hello World", public=True).json()
# did = new_doc["id"]
# wid = new_doc["defaultWorkspace"]["id"]

# details = c.get_document(did)
# print(details.json())

# asm = c.create_assembly(did, wid, name="Test Assembly")

# if asm.json()["name"] == "Test Assembly":
#     print("Assembly created")
# else:
#     print("Error: Assembly not created")

# c.del_document(did)
# trashed_doc = c.get_document(did)
# if trashed_doc.json()["trash"] is True:
#     print("Document now in trash")
# else:
#     print("Error: Document not trashed")