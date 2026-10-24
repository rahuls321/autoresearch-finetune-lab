# LazyDecider — Slide Deck Narration

Conversational, presenter-style narration: it *summarizes* each slide and adds color
rather than reading the slide text. The slide carries the detail; the voice carries
the story. One `## Slide N` block per slide; quoted (`>`) lines are the spoken text.
Voiced locally with macOS `say` (Daniel), synced slide-by-slide.

## Slide 1 — Title
> So this is LazyDecider. The short version: I taught an open-weight agent to fine-tune a model for me — while I slept.

## Slide 2 — The problem
> It started with a chore I hated: babysitting hyperparameters. Tweak, train, stare, repeat. So I made it run overnight instead.

## Slide 3 — The task
> The model's job is making calibrated decisions across four domains. What matters isn't just getting the answer right — it's matching the full confidence distribution.

## Slide 4 — The model
> Underneath it's a small, point-eight billion model with a decision head, trained with LoRA on a laptop. The agent gets to play with the usual knobs.

## Slide 5 — The overnight loop
> Here's the whole loop. Gemma proposes a config, a pruner trains it, we keep it only if it actually wins — and Tinker double-checks the result. And Gemma never touches the test set.

## Slide 6 — ASHA
> The pruner is the trick that makes this cheap. Bad configs get killed in the first few minutes, so the night isn't wasted on losers.

## Slide 7 — The real search
> And this is what Gemma actually did — five configs, verbatim from the log. The pattern's the interesting part: it kept the winners and reverted everything that didn't beat them. It even let go of a run with higher accuracy, because the loss was worse.

## Slide 8 — The decisive move
> If there was one big moment, it was this one. Gemma decided to unfreeze the backbone — and the loss just dropped. That single call was the night's biggest win.

## Slide 9 — Learning curves
> You can literally see it here. That one config pulls away from the pack and never looks back.

## Slide 10 — Can't cheat
> Now, the part I care about most. Early on the agent found a winner way too fast — turns out it was gaming a weak metric. It wasn't cheating; it was doing exactly what I asked. So I sealed everything: the test, the scorer, the budget, the configs. No room to fool itself.

## Slide 11 — Results
> And the payoff on the sealed test: a tiny model that matches the distribution almost perfectly — for basically zero dollars.

## Slide 12 — Per-domain
> Break it down by domain and it's strongest on invoices — which is exactly the case the live playground lets you try yourself.

## Slide 13 — Tinker referee
> To be sure I wasn't fooling myself, Tinker re-ran the recipe on a bigger model, in the cloud, on the same sealed test. It cleared the baseline comfortably — different model, same result.

## Slide 14 — Why open
> And this only works because everything's open. Free overnight reasoning, a model I fully own, and guardrails anyone can audit. A closed API can't give you all three.

## Slide 15 — The lazy payoff
> So that's the lazy payoff. I wake up, read what it tried, retrain the winner in one command — and never babysit a sweep again.
