from pyModbusTCP.client import ModbusClient
import json

with open("config.json", "r") as f:
    config = json.load(f)

# Setările pentru conexiune
modbus_host = config["controllers"]["ET-7052"]
modbus_port = int(config["controllers"]["port"])

# Creează clientul Modbus
client = ModbusClient(host=modbus_host, port=modbus_port, auto_open=True, auto_close=True)

# Citește un singur registru holding de la adresa 0
register_address = 0
register_count = 1

# Trimite cererea de citire
#regs = client.read_input_registers(register_address, register_count)

digital_outputs = client.read_coils(0, 2)

for x in digital_outputs:
    print(x)

"""if regs:
    print(f"Valoarea registrului la adresa {register_address}: {regs[0]}")
else:
    print("Eroare la citirea registrului.")"""
