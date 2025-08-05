# download_models.py
from gpt4all import GPT4All
import os
import glob

# Create models directory
os.makedirs('/app/models', exist_ok=True)

# Download models
print('Downloading orca-mini-3b model...')
model1 = GPT4All('orca-mini-3b-gguf2-q4_0.gguf', model_path='/app/models')
print('orca-mini-3b downloaded successfully')

print('Downloading Meta-Llama-3-8B model...')
model2 = GPT4All('Meta-Llama-3-8B-Instruct.Q4_0.gguf', model_path='/app/models')
print('Meta-Llama-3-8B downloaded successfully')

# Verify
models = glob.glob('/app/models/*.gguf')
print(f'Downloaded models: {models}')
