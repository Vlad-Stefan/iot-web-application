from pyModbusTCP.client import ModbusClient

class Controller:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def update(self):
        print("To be implemented by subclasses")

    def set_output_on(self, index):
        print("To be implemented by subclasses")

class ICPDAS(Controller):
    def __init__(self, host, port):
        super().__init__(host, port)

    def read_analog_inputs(self, register_address, register_count):
        self.client = ModbusClient(host=self.host, port=self.port, auto_open=True, auto_close=True)
        result = self.client.read_input_registers(register_address, register_count)
        self.client.close()
        if result is None:
            raise Exception(f"Eroare la citirea intrărilor digitale de la adresa {register_address}")
        return result

    def read_digital_outputs(self, addressa, count):
        self.client = ModbusClient(host=self.host, port=self.port, auto_open=True, auto_close=True)
        result = self.client.read_coils(addressa, count)
        self.client.close()
        if result is None:
            raise Exception("Nu s-au putut citi ieşirile digitale")
        return result
    
    def set_output(self, out, value):
        self.client = ModbusClient(host=self.host, port=self.port, auto_open=True, auto_close=True)
        success = self.client.write_single_coil(out, value)
        self.client.close()
        if not success:
            raise Exception(f"Eroare la activarea DO{out}")
        return True
 
class ET_7017(ICPDAS):
    def __init__(self, host, port):
        super().__init__(host, port)

    def update(self, values_dict):
       valori = self.read_analog_inputs(0, 1)
       values_dict['ET-7017'] = valori[0] if valori else None

class ET_7052(ICPDAS):
    def __init__(self, host, port):
        super().__init__(host, port)
    
    def update(self, values_dict):
        valori = self.read_analog_inputs(0, 1)
        values_dict['ET-7052'] = valori[0] if valori else None

class Senzori:
    def __init__(self):
        self.valori = {
            "ET7017": None,
            "DO0": None,
        }

        self.controllers = [
            ET_7017("10.10.24.15", 502),
            ET_7052("10.10.24.14", 502)
        ]

    def update(self):
        for ctrl in self.controllers:
            ctrl.update(self.valori)

    def get_valori(self):
        return self.valori

    

