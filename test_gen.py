import logging
logging.basicConfig(level=logging.INFO)
from backend.rag.rag_pipeline import RAGPipeline

rag = RAGPipeline()
print('[1] Pipeline loaded')
print('[3] Starting generation')
count = 0
for token in rag.chat_engine.stream_generate('What is diabetes?', 'context', timeout=10.0):
    count += 1
    print('TOKEN:', token)
print('DONE', count)
