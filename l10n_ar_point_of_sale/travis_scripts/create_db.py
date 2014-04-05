import xmlrpclib
sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/db')

# Para crear una BD
sock.create_database("admin", "testdb", True, "en_US")
