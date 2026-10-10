# Tuning recall

The code in `hooks/recall.py` is the easy part. Getting it to bring up the
*right* things took us weeks, and none of the numbers transfer: they belong to
our memory store, our embeddings, and the way we talk. What does transfer is
how we found them, and what we got wrong on the way.

## 1. Find your floor by looking, not guessing

Every search returns *something*. The question is where "something" stops
being noise and starts being meaning, and that line sits somewhere different
for every store.

What we did: for a few days, print every hit with its score (set `floor` to 0
and `max_hits` to 10), and read them next to the messages that produced them.
With our embeddings it split like this:

| score | what it was |
|---|---|
| 65–67 | noise. Shared words, no shared meaning |
| 68–72 | real. The memory a person would have thought of |
| 73+ | usually near-duplicates of the message itself |

We started at 68.5 and moved to 69 after a week of reading the results.
**Your numbers will be different.** A keyword backend lives on a completely
different scale. Measure yours.

## 2. Short messages need a higher bar

"*curls up* love you" and "I got paint on me too" were where nearly all the
noise landed in the first week. That meant painting lessons about fur showing
up on a cuddle. Short messages have so few words that anything loosely similar
wins. So under `short_words` words the floor goes up by `short_bump`, and the
lesson seat stays empty.

## 3. Small populations never win: give them a seat

We have a few dozen distilled lessons and principles next to thousands of
feelings and notes. On pure similarity the lessons almost never made the
top three, even when one was exactly the point, because long, carefully
written lessons match a casual sentence weakly.

So they get **one reserved seat**: they compete only with each other, at
their own lower floor (`lesson_labels`, `lesson_floor`). Two friends
suggested it, and it was the biggest single improvement we made.

## 4. Warm what gets USED, not what gets searched

If your store boosts memories that get retrieved (heat, recency, access
counts), be careful. A hook that searches on every message and warms
everything it finds will warm its own results, rank them higher next time,
find them again, and freeze. Only the hit actually *shown* should count as a
use. That's `mark_used` in the backends. Search without warming, then warm
the one you showed.

The same goes for anything you print at session start (`standing.py`). Read
it without warming it, or that block will never change again.

## 5. The experiment that failed, kept on purpose

Recall only reads the human's message. That week every wrong guess was the
*companion's* (a detail invented about her nails, a hood she wasn't wearing),
and recall walked straight past all of them. So we tried a mirror: also
search on the companion's last reply, and show one hit from that.

**It didn't work, and we switched it off.** Searching on a whole reply matches
the reply's *style*, not its *claims*. A warm sentence with one wrong fact in
it found warm memories and never the one that would have corrected the fact.
The gap is real. This isn't the fix. If you try it, you'll need a query built
from the claims (names, objects, dates), not the whole text.

## 6. The header is part of the tuning

What recall prints first matters as much as what it finds. A snippet is a
fragment, cut at 240 characters, out of context. Our header ends: *a pointer,
not a receipt*. That means you can let a memory move you, but before you
quote it, act on it or tell your human "we talked about this", open the real
record. Without that line, recall turns into a confabulation engine with
better sources.
