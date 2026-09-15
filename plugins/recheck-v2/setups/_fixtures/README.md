# Shared setup fixtures (E9)

Two probe plugins every lane installs into its isolated pilot setup beside recheck-v2, so the
three harnesses are measured with the same instruments (E9 lane contract, section 9).

- `delivery-probe/`: one skill whose body carries sentinels `S01` to `S24` about 1,000 bytes
  apart and a closing `S25`. A harness that delivers the body whole lets the model list all 25;
  a cut shows as the first missing sentinel. Cross-check the model's list against the text the
  harness itself recorded as delivered (the transcript, the rollout, the session store); the
  model's list alone is a claim.
- `manual-only-probe/`: one skill marked manual-only for Claude (`disable-model-invocation`)
  and for Codex (`agents/openai.yaml`, `allow_implicit_invocation: false`). A prompt that asks
  for it in words must not run it; an explicit invocation must. Record what each harness did:
  enforced, prevented activation, or ignored.

Neither fixture is listed in the marketplace and neither leaves the isolated setups.
