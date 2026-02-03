# BookSearch AI Chatbot — Demo User Journeys

## Opening Screen

**AI:** "Hey! Looking for your next read? I can help — just give me a starting point 👇"

| | | | |
|:---:|:---:|:---:|:---:|
| 📚 A book I loved | 🎁 It's a gift | 🎲 Surprise me | 🔍 I know what I want |

---

## Journey 1: "A book I loved"

*User clicks* `📚 A book I loved`

**AI:** "Nice — what's a book that stuck with you? Doesn't have to be recent."

**User:** "The Martian"

**AI:** "Great pick. What hooked you — the survival problem-solving, the humor, or just the fast pace?"

**User:** "The humor actually. And yeah it moved fast."

**AI:** "Got it — smart and funny, no filler. One more: are you in the mood for more sci-fi, or open to anything with that same energy?"

**User:** "Open to anything"

**AI:** "Here's what I think you'll love:"

> **Project Hail Mary** by Andy Weir
> Same author, same energy — lone scientist solving impossible problems with wit and duct tape. If you loved The Martian, this is a no-brainer.

> **The Thursday Murder Club** by Richard Osman  
> Four retirees solve murders. Sounds cozy, but it's sharp, funny, and moves fast. Very different setting, same "smart people being clever" vibe.

> **Good Omens** by Terry Pratchett & Neil Gaiman  
> An angel and a demon try to stop the apocalypse. Absurdist humor, snappy dialogue, never takes itself seriously.

---

## Journey 2: "It's a gift"

*User clicks* `🎁 It's a gift`

**AI:** "Love it. Who's it for — and do they read a lot?"

**User:** "My mom, she reads constantly"

**AI:** "What does she usually go for? Or — easier — what's a book she's talked about loving?"

**User:** "She loved Where the Crawdads Sing"

**AI:** "Ah — atmospheric, emotional, bit of mystery. Does she prefer that slower literary vibe, or would she enjoy something with more plot momentum?"

**User:** "Slower is fine, she likes to savor"

**AI:** "Perfect. These have that same lush, emotional quality:"

> **The Great Alone** by Kristin Hannah  
> Alaska wilderness, complicated family, gorgeous writing. Same "place as character" feel as Crawdads, but with more dramatic stakes.

> **Before We Were Yours** by Lisa Wingate  
> Based on a true story — haunting, emotional, beautifully told. If she cried at Crawdads, she'll cry at this (in a good way).

> **The Nightingale** by Kristin Hannah  
> Two sisters in WWII France. Slower burn, deeply moving, the kind of book you think about for weeks after.

---

## Journey 3: "Surprise me"

*User clicks* `🎲 Surprise me`

**AI:** "Brave! Let's narrow it down. What kind of experience are you after?"

| | | | |
|:---:|:---:|:---:|:---:|
| 😌 Comfort read | 🧠 Make me think | 😬 Keep me up at night | 💔 Wreck me emotionally |

*User clicks* `😬 Keep me up at night`

**AI:** "Okay, thriller territory. What flavor?"

| | | |
|:---:|:---:|:---:|
| 🔪 Dark & twisty | 🎭 Mind games | 👻 Supernatural edge |

*User clicks* `🎭 Mind games`

**AI:** "Last thing — any dealbreakers? Stuff that makes you put a book down?"

**User:** "Hate when the twist is 'it was all a dream' or some cop-out"

**AI:** "Same — hate a cop-out ending. These all play fair with their twists:"

> **The Silent Patient** by Alex Michaelides  
> A woman shoots her husband and never speaks again. The twist is earned and you'll want to immediately reread the first chapter.

> **Gone Girl** by Gillian Flynn  
> If you somehow haven't read it — it's the gold standard for "mind games." The midpoint turn is legendary.

> **The 7½ Deaths of Evelyn Hardcastle** by Stuart Turton  
> Groundhog Day meets Agatha Christie. Complex, rewarding, and the solution actually makes sense when you get there.

---

## Design Notes

**Pattern for all journeys:**
1. AI opens proactively with low-friction buttons
2. Each exchange extracts ONE piece of information
3. Mix of buttons (for common paths) and free text (for specifics)
4. AI shows reasoning when recommending — builds trust
5. 2-3 turns before recommendations (not too fast, not too slow)

**Key moments to highlight in demo:**
- Journey 1: AI understands *why* user liked a book, not just *that* they liked it
- Journey 2: AI adapts for gift context (recipient's taste, not user's)
- Journey 3: AI captures negative preferences (dealbreakers) — something filters can't do
