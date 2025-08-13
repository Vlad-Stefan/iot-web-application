from lib.controller import ICPDASController

class AnalogController(ICPDASController):
    def read_analog_inputs(self, register_address, register_count):
        result = self.client.read_input_registers(register_address, register_count)
        if result is None:
            raise Exception(f"Eroare la citirea intrărilor digitale de la adresa {register_address}")
        return result