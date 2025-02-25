# Open Deep Research

Welcome to this open replication of [OpenAI's Deep Research](https://openai.com/index/introducing-deep-research/)!

Read more about this implementation's goal and methods [in our blog post](https://huggingface.co/blog/open-deep-research).

This agent achieves 55% pass@1 on GAIA validation set, vs 67% for Deep Research.

To install it, first run
```bash
pip install -r requirements.txt
```

And install smolagents dev version
```bash
pip install "smolagents[dev]"
```

add your huggingface token to the .env file
```bash
HF_TOKEN=your_huggingface_token_here
```

Then you're good to go! Run the run.py script, as in:
```bash
python run.py --model-id "o1" "Your question here!"
```
