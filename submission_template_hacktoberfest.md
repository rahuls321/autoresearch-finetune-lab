---
title: "LazyDecider: I taught an open-weight agent to fine-tune a model while I slept"
published: false
tags: devchallenge, hf26challenge, machinelearning, opensource
cover_image: https://raw.githubusercontent.com/rahuls321/autoresearch-finetune-lab/main/artifacts/lazydecider_cover.png
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built

I am lazy in the specific way engineers are lazy: I will happily spend a week automating a job that
takes ten minutes, as long as I never have to do the ten minutes again. The ten-minute job here is
**hyperparameter babysitting** — change the learning rate, kick off a run, stare at a loss curve,
change the LoRA rank, repeat until the model is good or you're asleep at your desk.

So I flipped it. **LazyDecider** is a small overnight lab that fine-tunes a decision model *while I
sleep*. A **local, open-weight agent (Gemma 4 E4B)** reads the experiment log, proposes one training
config with a one-line reason, an **ASHA** pruner trains it and kills it early if it's losing, and the
run is **kept only if it beats the current best** on a frozen split — otherwise reverted. In the
morning the winner is retrained once and scored on a **sealed** test set, and a **Tinker** run confirms
the recipe transfers to a bigger model.

The effort it saves: I never babysit a hyperparameter sweep again. I wake up, open `REPORT.md`, and
read what the agent tried, why, and which config won — for ~$0, on a laptop, with no cloud meter
spinning overnight.

**The result:** a 0.8B decision model found autonomously that lands **0.770 accuracy** and a very low
**KL-from-gold of 0.094** on a sealed test — the metric that actually matters on this benchmark — with
its strongest trained domain being invoice processing at **0.840**.

| Model | Role | Accuracy ↑ | KL from gold ↓ | Brier ↓ | ECE ↓ |
|---|---|---:|---:|---:|---:|
| Prior / Uniform | reference | ~0.470 | — | — | — |
| Zero-shot base | no training | 0.483 | — | — | — |
| **Tinker 4B (confirm)** | cloud referee | 0.601 | 0.642 | 0.172 | 0.094 |
| **LazyDecider 0.8B** | **the winner** | **0.770** | **0.094** | **0.051** | 0.145 |

## Demo

There are three ways to see LazyDecider, from "just look" to "run it yourself":

**1. Interactive UI — the night dashboard (hosted on Render):** https://lazydecider-demo.onrender.com

A static web page that replays the **real** overnight run from the committed logs: Gemma's config
proposals and one-line reasons, the ASHA **keep/revert** decisions, the learning-curve and results
charts, and the sealed-test table. Nothing is faked — it reads the actual experiment log.

**2. Hands-on playground — run the real model (local):** a Gradio app that loads the real 0.8B model
(`artifacts/best_model`) and decides on an invoice you configure. It's embedded in the UI above under
*"▶ Try it yourself"*, and runs locally in three commands:

```bash
git clone https://github.com/rahuls321/autoresearch-finetune-lab
cd autoresearch-finetune-lab
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python unsloth gradio
.venv/bin/python src/playground.py            # opens http://127.0.0.1:7860
```

**3. Walkthrough video (~3.5 min, narrated):** a guided tour — the task and model, the exact configs
Gemma proposed with the ASHA keep/revert calls, the "can't cheat" guardrails, and every sealed-test
number — ending with a **live playground finale** where the real 0.8B model is driven on three
invoices: a clean match returns `approve · 83%`, an over-invoiced case is flagged for `review`, and an
under-delivered case returns `manual review`.

{% embed https://lazydecider-demo.onrender.com/assets/lazydecider_slides.mp4 %}

<!-- Note: DEV may not play a raw .mp4 inline. If it doesn't render, either link it as above or
     upload artifacts/demo_video/lazydecider_slides.mp4 to YouTube and embed that URL instead:
{% embed <YOUTUBE_URL> %} -->


## Code

{% embed https://github.com/rahuls321/autoresearch-finetune-lab %}

Reproduce the pipeline in a few commands (full version in the README):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python datasets unsloth tinker
.venv/bin/python src/prepare_data.py       # download, seal, split
bash src/run_gemma_search.sh               # let Gemma search overnight
```

## How I Built It

Two **open** partners do the heavy lifting, and that's deliberate:

- **Gemma 4 E4B** is the *researcher*. It runs on my laptop through LM Studio's MLX build — fully
  offline, zero cost per call — and genuinely reasons about what to try next. These are **verbatim**
  one-line reasons from the real log (`source: gemma`):
  - *run 1 (kept):* "Establish a standard fast head-only baseline with cosine schedule and zero label smoothing on soft targets."
  - *run 2 (kept):* "Enable LoRA fine-tuning on the backbone to see if adapted encoder representations improve beyond the head-only baseline."
  - *run 3 (reverted):* "Introduce label smoothing and increased weight decay on the unfrozen backbone to improve calibration while preserving high accuracy."

  Run 2 — Gemma's call to unfreeze the backbone with LoRA — dropped validation loss **1.04 → 0.84**,
  the single biggest jump of the night. Runs 3–5 chased calibration, landed close, and were reverted.
  That keep-or-revert discipline is the difference between a search and a random walk.
- **Tinker** (Thinking Machines) is the *independent referee*. It fine-tunes a larger `Qwen3.5-4B`
  with LoRA in the cloud, under a hard dollar cap, and re-scores on the **same** sealed test — a clear
  lift over the zero-shot baseline (**0.601 vs 0.483**). Different model, different hardware, same
  ruler: proof the pipeline isn't fooling itself.
- The base model is `unsloth/Qwen3.5-0.8B` + a Clef joint-decision head, LoRA fine-tuned with
  **Unsloth**; the live demo UI is a dependency-free static site **hosted on Render**.

**The "can't cheat" part.** Early on, before guardrails, the loop found a "great" config suspiciously
fast — a too-small validation subsample let a lucky run look like a winner. The agent wasn't cheating;
it was optimizing the number I gave it. The lesson of autonomous tuning: *your agent will optimize your
metric, not your intent.* So I locked it down: the **test set is sealed** (only its SHA-256 is
committed; the worker literally can't read the cases), the **scorer copies the dataset's grading
arithmetic verbatim**, the worker **strips `TINKER_*` from its environment** so the free local loop
can't spend a cent, and every finalist's config is **committed to git before** its one-shot sealed read.

## Why Does Open Innovation Matter?

This whole thing only works *because* the pieces are open:

- The **agent and the model are both open weights**, so the entire lab runs on a laptop. Hundreds of
  reasoning calls a night cost exactly nothing — a cloud API would turn "run it every night" into a
  habit with a monthly bill.
- The resulting model is **yours**. Run it offline, inspect it, push the adapter to Hugging Face, fork
  the recipe. Nothing is trapped behind someone else's endpoint.
- Open weights make the guardrails **auditable**. "Can't cheat" is only credible when anyone can read
  the sealing logic and the scorer and check for themselves.

A closed API couldn't give me all three: free unlimited overnight reasoning, a model I fully own and
can run offline, and a pipeline whose integrity anyone can verify.

## The Lazy Payoff

I wake up, open `REPORT.md`, and read what Gemma tried, why, and which config won — then one command
retrains it and Tinker confirms it. The ten-minute job I automated (babysitting hyperparameter sweeps)?
I never do it again — it happens while I sleep, for free, on my own laptop.

## Prize Categories

- **Best Use of Render** — the live demo UI is hosted on Render as a static site, deployed straight
  from `render.yaml` with zero build config: https://lazydecider-demo.onrender.com
- **Best Use of Gemma** — Gemma 4 E4B is the autonomous researcher proposing every config locally and
  for free, with a real, reasoned experiment log.
- **Best Use of Tinker** — a dollar-capped `Qwen3.5-4B` LoRA confirm run that lifts clearly over the
  zero-shot baseline (0.601 vs 0.483) and independently validates the recipe.

<!-- Optional: My Agent Session — judges love this. Save your build session with DevRelay and embed it
     with the agent_session tag, or paste a link:
## My Agent Session
{% agent_session <YOUR_DEVRELAY_URL> %}
-->

<!-- Thanks for participating! -->
