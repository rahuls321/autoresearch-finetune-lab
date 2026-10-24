# LazyDecider — Slide Deck Narration

Per-slide narration for the walkthrough video. One `## Slide N` block per deck slide;
quoted lines (`>`) are the spoken text. Voiced locally with macOS `say` (Daniel),
synced slide-by-slide. Mirrors `artifacts/demo_voiceover.md` format so
`src/make_slides_voiceover.py` can parse it.

## Slide 1 — Title
> LazyDecider. I taught an open-weight agent to fine-tune a decision model for me — proposing configs, pruning the losers, keeping only the winners — all while I slept. It runs locally, on open weights, for about zero dollars.

## Slide 2 — The problem
> The job I refused to do again is hyperparameter babysitting. Change the learning rate, start a run, stare at a loss curve, change the LoRA rank, repeat until you fall asleep. So I automated it — the search now runs overnight, and I just read a report in the morning.

## Slide 3 — The task
> The task is typed decisions. The model reads a case and makes a calibrated call across four domains — invoices, customer service, security incidents, and agent traces — scored against a teacher consensus we call gold. The metric that really matters is K-L from gold: how well the whole probability distribution matches, not just the top answer.

## Slide 4 — The model
> Under the hood we fine-tune a point-eight billion parameter Qwen base model, plus a joint-decision head that emits a probability over every decision. It trains with Unsloth and LoRA on an eighteen-gigabyte Mac. The agent gets two real knobs: whether to unfreeze the backbone, and the usual LoRA and regularization settings.

## Slide 5 — The overnight loop
> Here's the loop. Gemma reads its own history and proposes one config with a one-line reason. An ASHA pruner trains it and kills it early if it's losing. We keep it only if it beats the current best on a frozen split — otherwise we revert. Finally, Tinker re-checks the recipe on a bigger model. Crucially, Gemma never sees the sealed test.

## Slide 6 — ASHA
> Why ASHA? Because you don't want to waste the whole night on a bad config. It evaluates at rungs — twenty, sixty, a hundred-forty, two-forty steps — and prunes the weak runs early, letting only the promising ones train to the end. A bad idea costs minutes, not hours.

## Slide 7 — The real search
> And here's what Gemma actually tried, verbatim from the log. Five configs. Run one, a frozen head-only baseline — kept. Run two, unfreeze the backbone with LoRA — kept, and it's the winner. Runs three, four, and five chased calibration but didn't beat run two's loss, so every one of them was reverted. Notice run three even had slightly higher accuracy, but higher loss — so the loop correctly let it go.

## Slide 8 — The decisive move
> Run two was the one big move of the night. Gemma's own words: enable LoRA on the backbone to see if adapted representations beat the head-only baseline. That single call dropped the select loss from one-point-oh-four to zero-point-eight-four, and lifted accuracy by twenty-six points. The agent found it on its own.

## Slide 9 — Learning curves
> You can see it in the curves. Run two, the unfrozen LoRA config, separates from the pack by rung one-forty and holds the lead all the way to the end. Everything else converges higher.

## Slide 10 — Can't cheat
> Now the part I care about most: it can't cheat. Early on, the loop found a winner suspiciously fast — a too-small validation sample let a lucky run look great. The agent wasn't cheating; it was optimizing the number I gave it. So I locked it down. The test is sealed — only its hash is committed. The scorer copies the dataset's grading arithmetic exactly. The local loop can't spend a cent on Tinker. And every finalist's config is frozen in git before its one-shot sealed read.

## Slide 11 — Results
> The results, on the sealed test. Our point-eight billion winner lands seventy-seven percent accuracy and a K-L from gold of just zero-point-oh-nine-four — the metric this benchmark actually optimizes — for about zero dollars on a laptop.

## Slide 12 — Per-domain
> Broken down by domain, the model is strongest on invoice processing at eighty-four percent, and best-calibrated on security incidents. Invoices are its best trained domain — which is exactly what the live playground demonstrates.

## Slide 13 — Tinker referee
> Tinker is the independent referee. A different model — a four-billion Qwen — on different, cloud hardware, scored on the same sealed test. It lifts clearly over the zero-shot baseline, zero-point-six-oh versus zero-point-four-eight, under a hard two-dollar spend cap. Different model, same ruler: the pipeline isn't fooling itself.

## Slide 14 — Why open
> Why does open matter here? Three reasons. The agent and the model are both open weights, so hundreds of reasoning calls a night cost nothing. The model is fully mine — I can run it offline and fork the recipe. And the guardrails are auditable — can't-cheat is only believable when anyone can read the sealing logic. A closed API couldn't give me all three.

## Slide 15 — The lazy payoff
> That's the lazy payoff. I wake up, open the report, read what Gemma tried and why, run one command to retrain the winner, and Tinker confirms it. I never babysit a hyperparameter sweep again. Open agent, open model, sealed test — built on a laptop, while asleep.
