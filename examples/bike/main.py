import onshape_api as osa
from onshape_api.map import traverse_assembly

# Initialize the client with the constructed path
client = osa.Client()
doc = osa.Document.from_url(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)

elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

variables["wheelDiameter"].expression = "300 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "30 deg"

client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
assembly = client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id)

traverse_assembly(assembly)

