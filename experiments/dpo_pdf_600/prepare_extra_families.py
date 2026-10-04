"""Create isolated runners for Llama, Gemma and Mistral; no downloads."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MODELS={
 'llama':('meta-llama/Llama-3.2-3B-Instruct',False),
 'gemma':('google/gemma-3-1b-it',True),
 'mistral':('mistralai/Mistral-7B-Instruct-v0.3',True),
}
HELPER='''
def adapt_messages(messages):
    # Deterministic serialization compatibility; retain all instruction text.
    if MERGE_SYSTEM and messages and messages[0]['role'] == 'system':
        if len(messages)<2 or messages[1]['role']!='user':
            raise ValueError('Atteso system seguito da user.')
        return [{'role':'user','content':messages[0]['content']+'\\n\\n'+messages[1]['content']}] + messages[2:]
    return messages

'''
def replace_all(text,mapping):
 for a,b in mapping.items():
  assert a in text,a
  text=text.replace(a,b)
 return text

def main():
 for family,(model,merge) in MODELS.items():
  runid=model.replace('/','__')
  policy='merge_system_into_first_user' if merge else 'native_roles'
  code=(ROOT/'train_smollm3_600.py').read_text(encoding='utf-8')
  code=replace_all(code,{
   "BASE = 'HuggingFaceTB/SmolLM3-3B'":f"BASE = {model!r}\nMERGE_SYSTEM = {merge!r}\n"+HELPER,
   'Training diagnostico DPO, Qwen2.5-3B-Instruct + NF4 + LoRA.':f'Training DPO {model} + NF4 + LoRA.',
   'Questo trainer e dedicato a SmolLM3-3B senza extended thinking.':f'Trainer dedicato a {model}.',
   'rendered = maybe_apply_chat_template(row, tokenizer, enable_thinking=False)':
    "rendered = maybe_apply_chat_template({**row, 'prompt': adapt_messages(row['prompt'])}, tokenizer)",
   "'chat_template_kwargs': {'enable_thinking': False},":f"'chat_template_kwargs': {{}}, 'message_policy': {policy!r},",
   "'chat_template_kwargs', 'mode'":"'chat_template_kwargs', 'message_policy', 'mode'",
  })
  compile(code,f'train_{family}_600.py','exec')
  (ROOT/f'train_{family}_600.py').write_text(code,encoding='utf-8')
  code=(ROOT/'compare_test_600.py').read_text(encoding='utf-8')
  code=replace_all(code,{
   'import uuid':f'import uuid\n\nos.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "180")\nos.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")\nMERGE_SYSTEM = {merge!r}\n'+HELPER,
   'Qwen__Qwen2.5-3B-Instruct_train_v1':runid+'_train_v1',
   'qwen3b_test_v1':family+'_test_v1',
   "tokenizer = AutoTokenizer.from_pretrained(str(adapter))":f"if training['model'] != {model!r} or training.get('message_policy') != {policy!r}:\n        raise ValueError('Modello o adattamento dei messaggi non coerente con il training.')\n    tokenizer = AutoTokenizer.from_pretrained(str(adapter))",
   "'decoding': {'do_sample': False":f"'message_policy': {policy!r},\n        'decoding': {{'do_sample': False",
   "tokenizer.apply_chat_template(row['messages'], tokenize=False, add_generation_prompt=True)":
    "tokenizer.apply_chat_template(adapt_messages(row['messages']), tokenize=False, add_generation_prompt=True)",
  })
  compile(code,f'compare_test_{family}_600.py','exec')
  (ROOT/f'compare_test_{family}_600.py').write_text(code,encoding='utf-8')
  code=(ROOT/'run_smollm3.ps1').read_text(encoding='utf-8')
  code=replace_all(code,{'HuggingFaceTB/SmolLM3-3B':model,
    'HuggingFaceTB__SmolLM3-3B':runid,'train_smollm3_600.py':f'train_{family}_600.py',
    'compare_test_smollm3_600.py':f'compare_test_{family}_600.py','smollm3_test_v1':family+'_test_v1'})
  (ROOT/f'run_{family}.ps1').write_text(code,encoding='utf-8')
  print('Preparato:',family,model,'policy:',policy)

if __name__=='__main__':main()
