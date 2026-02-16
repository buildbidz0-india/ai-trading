import sys
import io

# Force stdout to use utf-8 encoding to support emojis
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI

client = OpenAI(
    base_url="https://lightning.ai/api/v1/",
    api_key="986ee665-9e10-43cf-b1c1-4fbfa2c573e7/zainimam841438/deploy-model-project",
)

completion = client.chat.completions.create(
    model="anthropic/claude-opus-4-6",
    messages=[
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello, world!"}]
      },
    ],
)

print(completion.choices[0].message.content)
