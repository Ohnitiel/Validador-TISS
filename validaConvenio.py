from lxml import etree
from lxml.etree import XMLSyntaxError

def validaConvenio(doc, reg_ANS):
    planos = eval(open('registro ANS.txt').read())
    plano = planos[reg_ANS]
    schema = etree.XMLSchema(f"xsd/{plano}.xsd")
    schema.validate(doc)
    
    return schema