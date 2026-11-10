"""Sequentially run three already-frozen, explicitly selected N-hash probes."""
from pathlib import Path
import hashlib,subprocess,sys
R=Path(__file__).resolve().parents[2]
expected={1:'3c84a44668513e5af02eecbd40b3f0d02079af1b790b48b42a1cd6b5eeb2a2cc',2:'b121285e71c238cb8a0f5b47800eed81be6b356c1ce3f22e01027ce41ef94396',3:'ef9c832a962d708cdef22b3e95add4a61c9a63431de31de19132e816e525abec'}
for seed,sha in expected.items():
 name=f'oracle_495_525_nhash_{seed}';p=R/f'data/experiments/blackbox_20261105/{name}.cpp'
 if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise RuntimeError('Selected frozen probe mismatch')
 print(f'FIXED HASH {seed}: one selected round; next starts only after confirmed completion',flush=True)
 r=subprocess.run([sys.executable,'-X','utf8',str(R/'dev/tools/continue_20261105.py'),'--name',name,'--source',str(p),'--description',f'Fixed N checksum seed{seed} on same5 certified zero witnesses in495..525. Label-conditioned padding splitmix64(N+seed*C)&63, range0..63. Loss from110826 is exact sum hash; physical/virtual prefixes and score>=80 guard unchanged. Keep all multiset solutions, no forced identity.'],cwd=R)
 if r.returncode!=0:
  print('Stopping fixed batch: unfinished or failed task must be resumed, never uploaded again.',flush=True)
  raise SystemExit(r.returncode)
print('All three fixed hash rounds registered; no further upload selected by this script.',flush=True)
