from opcua import Client
from opcua import ua

# Set up the OPC UA client to connect to the server
url = "opc.tcp://127.0.0.1:4840"
client = Client(url)

# Set username and password for authentication
username = "Admin"
password = "password"

client.set_user(username)
client.set_password(password)

client.connect()

try:
    # Connect to the server
    client.connect()
    print(f"Connected to OPC UA server at {url} with user '{username}'")

    # Replace with the NodeId of the tag you want to read
    tag_to_read = "ns=6;s=::Logic:counter"  # Adjust this to the correct namespace and node ID
    node = client.get_node(tag_to_read)

    # Read the value
    value = node.get_value()
    print(f"Read value: {value}")

    # Write a new value to the tag
    tag_to_write = "ns=6;s=::Logic:countUp"  # Adjust this to the correct namespace and node ID
    new_value = True  # Replace this with the desired value
    node_to_write = client.get_node(tag_to_write)
    print('Got the node')
    node_to_write.set_value(new_value)

    print(f"Written new value: {new_value} to tag {tag_to_write}")

finally:
    # Disconnect the client
    client.disconnect()
    print("Disconnected from OPC UA server")
