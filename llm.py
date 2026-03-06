from transformers import AutoTokenizer, AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B"
)