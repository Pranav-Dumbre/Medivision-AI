import time, threading
from transformers import AutoTokenizer, TextIteratorStreamer

t = AutoTokenizer.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')
streamer = TextIteratorStreamer(t, timeout=2.0)

def fake_gen():
    time.sleep(5)

th = threading.Thread(target=fake_gen)
th.start()
print('Waiting...')

try:
    for x in streamer:
        print(x)
except Exception as e:
    print('CAUGHT:', type(e))
