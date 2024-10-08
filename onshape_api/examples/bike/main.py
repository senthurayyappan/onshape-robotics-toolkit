import onshape_api as osa

client = osa.Client()
doc = osa.Document(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)

elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variable_studio_element = next(
    (element for element in elements if element.elementType == osa.ELEMENT_TYPE.VARIABLESTUDIO),
    None,
)
print(variable_studio_element)
