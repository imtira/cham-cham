import os
import wave
import struct
import sys

def read_wave(source, lsb):
    sound = wave.open(source, 'r')

    params = sound.getparams()
    sample_width = sound.getsampwidth()
    channels = sound.getnchannels()
    frames = sound.getnframes()
    samples = frames * channels

    if sample_width == 1:
        fmt = f'{samples}B'
        mask = (1 << 8) - (1 << lsb)
        sb = -(1 << 8)
    elif sample_width == 2:
        fmt = f'{samples}h'
        mask = (1 << 15) - (1 << lsb)
        sb = -(1 << 15)
    else:
        raise ValueError('Unsupported bit-depth')
    
    audio_data = list(struct.unpack(fmt, sound.readframes(frames)))

    return (params, samples, audio_data, sb, fmt, mask, frames)

def encode(source, tinput, output, lsb):
    params, samples, audio_data, sb, fmt, mask, frames = read_wave(source, lsb)

    available_bytes = (samples * lsb) // 8
    input_size = len(tinput.encode('utf-8'))

    if input_size > available_bytes:
        required = math.ceil(input_size * 8 / samples)
        raise ValueError(f'Input file too large. Requires {required}b,'
            f'have {available_bytes}b.')
    
    data_index = 0
    buffer = 0
    written_size = 0
    buffer_length = 0
    sound_index = 0
    values = []

    tinput = memoryview(bytes(tinput, 'utf-8'))

    done = False
    while not done:
        while buffer_length < lsb and data_index // 8 < len(tinput):
            buffer += (tinput[data_index // 8] >> (data_index % 8)) << buffer_length
            
            bits_added = 8 - (data_index % 8)
            written_size += bits_added
            data_index += bits_added
        
        current_data = buffer % (1 << lsb)
        buffer >>= lsb
        buffer_length -= lsb

        while sound_index < len(audio_data) and audio_data[sound_index] == sb:
            values.append(struct.pack(fmt[-1], audio_data[sound_index]))
            sound_index += 1
        
        if sound_index < len(audio_data):
            current_sample = audio_data[sound_index]
            sound_index += 1

            sign = 1
            if current_sample < 0:
                current_sample = -current_sample
                sign = -1
            
            altered_sample = sign * ((current_sample & mask) | current_data)

            values.append(struct.pack(fmt[-1], altered_sample))
        
        if data_index // 8 >= len(tinput) and buffer_length <= 0:
            done = True
    
    while sound_index < len(audio_data):
        values.append(struct.pack(fmt[-1], audio_data[sound_index]))
        sound_index += 1

    altered = wave.open(output, 'w')
    altered.setparams(params)
    altered.writeframes(b''.join(values))
    altered.close()

def decode(source, lsb, byte_count):
    params, samples, audio_data, sb, fmt, _, frames = read_wave(source, lsb)

    mask = (1 << lsb) - 1

    data = bytearray()
    sound_index = 0
    buffer = 0
    buffer_length = 0
    
    while byte_count > 0:
        next_sample = audio_data[sound_index]

        if next_sample != sb:
            buffer += (abs(next_sample) & mask) << buffer_length
            buffer_length += lsb
        sound_index += 1

        while buffer_length >= 8 and byte_count > 0:
            current_data = buffer % (1 << 8)
            buffer >>= 8
            buffer_length -= 8
            data += struct.pack('1B', current_data)
            byte_count -= 1
    
    print(data.decode('utf-8', 'ignore'))

def main():
    if len(sys.argv) < 3:
        print('Required: decode [SOURCE]\nor')
        print('encode [SOURCE] [INPUT] [OUTPUT]')
        return

    mode = sys.argv[1]

    source = sys.argv[2]
    lsb = 5
    
    if mode == "encode":
        finput = sys.argv[3]
        output = sys.argv[4]
        tinput = open(finput).read()

        encode(source, tinput, output, lsb)

    elif mode == "decode":
        decode(source, lsb, 100)

    else:
        print('bad mode')

if __name__ == '__main__':
    main()