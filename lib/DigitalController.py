from lib.controller import ICPDASController

class DigitalController(ICPDASController):
    def read_digital_outputs(self, addressa, count):
        result = self.client.read_coils(addressa, count)
        if result is None:
            raise Exception("Nu s-au putut citi ieşirile digitale")
        return result
    
    def set_output_on(self, index):
        success = self.client.write_single_coil(index, True)
        if not success:
            raise Exception(f"Eroare la activarea DO{index}")
        return True
    
    def set_output_off(self, index):
        success = self.client.write_single_coil(index, False)
        if not success:
            raise Exception(f"Eroare la dezactivarea DO{index}")
        return True