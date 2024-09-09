import asyncio
from asyncua.sync import Client, ua

ip = "localhost"
port = 4840
username = "Admin"
password = "password"

url = f"opc.tcp://{username}:{password}@{ip}:{port}/"

def main():

    print(f"Connecting to {url} ...")
    client = Client(url=url)
    client.connect()

    var = client.get_node("ns=6;s=::Logic:counter")

    value = var.read_value()
    print(f"Value of MyVariable ({var}): {value}")

    new_value = value + 20

    data_value = ua.DataValue(ua.Variant(new_value, ua.VariantType.Byte))
    var.write_value(data_value)

    client.disconnect()

if __name__ == "__main__":
    main()