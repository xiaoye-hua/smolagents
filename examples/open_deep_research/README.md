# Open Deep Research

Welcome to this open replication of [OpenAI's Deep Research](https://openai.com/index/introducing-deep-research/)!

Read more about this implementation's goal and methods [in our blog post](https://huggingface.co/blog/open-deep-research).

This agent achieves 55% pass@1 on GAIA validation set, vs 67% for Deep Research.



# How to use
## Step 1: config python env
```bash
# enter poetry env 
poetry shell
pip install -r requirements.txt
# And install smolagents dev version
pip install "smolagents[dev]"
```

## Step 2 environment variable 
add a `.env` file in the root directory
add your huggingface token and serpAPI key to the .env file
```bash
HF_TOKEN=your_huggingface_token_here
SERPAPI_API_KEY=your_serpapi_api_key
```
## Step 3
Then you're good to go! Run the run.py script, as in:
```bash
python run.py --model-id "o1" "Your question here!"
```
