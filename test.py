import sounddevice as sd
import soundfile as sf

filename = 'output.mp3'


devices = sd.query_devices()

device_id = sd._get_device_id(sd.default.device['output'], 'output')
print(device_id)
'''
for i, device in enumerate(devices):
    if device.get('max_input_channels') > 0:
        print("Input", device.get('name'))
    if device.get('max_output_channels') > 0:
        print("Output", device.get('name'))
'''
# Extract data and sampling rate from file
data, fs = sf.read(filename, dtype='float32')  

sd.play(data, fs, device = device_id)
status = sd.wait()  # Wait until file is done playing