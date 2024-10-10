import time

import onshape_api as osa

client = osa.Client()

doc = osa.Document(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)

elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

variables["wheelDiameter"].expression = "300 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "30 deg"

client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
time.sleep(2)


variables["wheelDiameter"].expression = "200 mm"
variables["wheelThickness"].expression = "91 mm"
variables["forkAngle"].expression = "30 deg"

client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
time.sleep(2)


variables["wheelDiameter"].expression = "250 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "30 deg"

# client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
# time.sleep(2)
print(client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id))

# print(client.get_features_from_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id))
