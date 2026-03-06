# Solving book discovery's hardest problem: When readers don't know what they want

**The most effective book recommendation approaches share a counterintuitive insight: asking readers what they dislike matters as much as asking what they love.** Services like StoryGraph have outperformed Goodreads by gathering multi-dimensional preference data—mood, pacing, content warnings—rather than relying on star ratings alone. Meanwhile, Reddit communities like r/BooksThatFeelLikeThis demonstrate massive demand for "vibe-based" discovery that algorithms can't provide. For an AI chatbot in a bookstore context, the research points to a clear design direction: model the skilled librarian's reader's advisory interview, capture both positive and negative preferences, and help readers articulate what they want through conversation rather than demanding it upfront.

## Traditional services struggle with shallow preference data

**Goodreads** requires users to rate at least **20 books** before its recommendation engine activates—a significant cold-start barrier. Even then, users widely describe its recommendations as "a joke used to promote whatever Amazon wants to sell." The platform collects only whole-star ratings and genre preferences, missing the nuanced qualities that make readers love specific books. Critics note the interface feels "like a relic from early web 2.0," with minimal feature updates since Amazon's 2013 acquisition.

**StoryGraph**, launched in 2019 as an Amazon-free alternative, takes a fundamentally different approach. During onboarding, it encourages importing Goodreads data (solving cold-start instantly) and runs a short questionnaire capturing mood preferences, desired pacing, and content to avoid. Its review system asks users to tag each book's emotional tone (adventurous, dark, hopeful), pacing (slow/medium/fast), and whether it's character-driven or plot-driven. Users can rate with **quarter-star precision**—a seemingly small feature that provides dramatically richer signal than Goodreads' whole-star system.

**Likewise**, backed by Bill Gates, requires users to add 10 favorite books during onboarding, then uses dating-app-style daily swipes to refine preferences. **Libby** recently introduced "Inspire Me," an AI feature using preset adjective tags like "spine-tingling" and "whimsical" rather than free-form chat—a constrained but effective approach for library patrons. **Libro.fm** rejects algorithms entirely, emphasizing "real booksellers write our recommendations, not algorithms."

## Mood-based discovery addresses the "I don't know" problem

The UK service **Whichbook** pioneered an elegant interface using sliding scales across emotional dimensions: Happy↔Sad, Funny↔Serious, Safe↔Disturbing, Predictable↔Unpredictable. Users adjust up to four sliders to indicate where they want their next read to fall on each spectrum. This captures preference information that genre tags cannot: someone wanting a "funny but slightly disturbing" book can express that directly.

StoryGraph's "What are you in the mood for?" feature lets users filter their own to-read pile by current emotional state. The insight is that reading preferences are **context-dependent**—the same reader wants completely different books when tired versus energized, stressed versus celebratory. Static preference profiles miss this dynamic.

Reddit's **r/BooksThatFeelLikeThis** community demonstrates demand for atmospheric matching at scale. Users post images, paintings, or music that capture a feeling, and the community responds with matching books. Requests like "books that feel like cats napping in flowers" or "a painting you need to feel like you're part of" receive precise recommendations that no algorithm could generate. A moderator noted: "This cannot be so easy, and yet, it is."

## Library science offers proven frameworks for understanding preferences

Librarian Nancy Pearl's **"Four Doorways"** framework identifies how readers enter books: through **Story/Plot** (page-turners), **Character** (feeling you've lost a friend when finished), **Setting** (powerful sense of place), or **Language** (savoring the prose). Most books have one or two dominant doorways, and readers tend to prefer books matching their personal doorway preference. Pearl's dream was attaching pie charts to every book showing these proportions—a concept now feasible with LLM-based analysis.

The **reader's advisory interview** technique from library science addresses the "I don't know what I want" problem through guided questioning. Skilled librarians start with open-ended questions ("Tell me about a book you really enjoyed"), then probe for appeal factors ("What did you enjoy about it?"). Critically, they ask about **negative preferences**: "Tell me about a book you didn't like and why." Brooklyn Public Library's BookMatch service, where librarians spend 30-40 minutes per request, proved "there's a lot in book recommendations that can't be artificially generated."

Joyce Saricks' **appeal factors** taxonomy, used in the NoveList database, provides vocabulary for capturing preferences: pacing (fast/intensifying/leisurely), tone (atmospheric/bittersweet/whimsical/haunting), character qualities (quirky/unreliable narrator/diverse cast), and storyline type (character-driven/plot-driven/world-building). These dimensions explain why readers like what they like far better than genre labels alone.

## Why algorithms fail and humans succeed

The core problem is what Literary Hub called "unquantifiable qualities"—voice, tone, philosophical outlook. As one analyst noted: "What is unquantifiable is horrifying to the corporate overlords, but it's the magic that connects readers with particular books." Algorithms using genre tags and collaborative filtering can identify that users who liked Book A also liked Book B, but cannot explain *why*—and the reason matters.

Reddit discussions reveal consistent frustrations: the same bestsellers recommended repeatedly regardless of stated preferences; popularity bias drowning out lesser-known titles; and the inability to express nuanced requests like "cozy mystery but not too cozy." Users report that **r/suggestmeabook** (2.5M+ members) consistently outperforms algorithms by handling hyper-specific requests that require human judgment: "a book set in space with a strong female protagonist, a happy ending, and an equally well-written sequel."

Academic research confirms hybrid approaches combining content-based and collaborative filtering outperform single methods, but a more telling finding is that **small improvements in offline accuracy metrics don't reliably translate to user satisfaction**. Netflix discovered they need "a pretty healthy dose of unpersonalized popularity" because highly accurate but obscure predictions feel wrong to users. The ultimate metric for books should be "finished and enjoyed," not "clicked on."

## AI-powered discovery is transforming the landscape

**ChatGPT and Claude** have become primary discovery tools for many readers. Users praise the ability to describe abstract preferences: "I want something that makes me cry, gasp, or both" or "sci-fi but not hard sci-fi, with sharp humor." The interactive refinement loop—providing feedback and getting adjusted suggestions—addresses limitations of static recommendation lists. ChatGPT's memory feature (since 2024) enables increasingly personalized recommendations across conversations.

Dedicated tools have emerged: **Readow.ai** asks for favorite books and pattern-matches across a million-title database. **Sona** (from Read This Twice) processes detailed natural language prompts. **Next Three Books** deliberately limits output to exactly three recommendations to reduce decision paralysis. **Find Your Next Book** provides single recommendations with explanations of matching logic.

Library systems are integrating AI search: **EBSCO's Natural Language Search** lets researchers type queries like "How does dehumanizing language affect us" and get relevant results that Boolean searches missed. Beta testers were "completely blown away by how the AI tool could retrieve relevant results from poorly structured searches."

The key differentiation from traditional approaches: LLMs enable **semantic search** (understanding meaning, not just keywords), **nuanced preference parsing** ("Outlander but without the time travel"), and **conversational context** that builds understanding across multiple exchanges. Queries that would be impossible to express in traditional filtering interfaces—"I want something literary but not pretentious"—become answerable.

## Anti-recommendations deserve equal weight

**Negative preferences are underutilized but critical.** Research on recommender systems identifies three uses: generating explicit avoid-lists, filtering results by negative attributes, and inferring positive preferences from negatives ("not like X" implies preferences). Psychological research supports this: negativity bias means disappointing recommendations have stronger impact than satisfying ones, making avoidance especially valuable for readers with specific sensitivities.

StoryGraph's crowdsourced **content warning system** with severity levels (graphic/moderate/minor) exemplifies effective implementation. Users can specify content to avoid—animal death, abuse, specific phobias—and matching books are filtered or flagged. This addresses a real pain point: non-neurotypical readers and those avoiding triggers need more than genre filtering.

The reader's advisory interview technique explicitly includes asking what readers *didn't* like. Librarians call these "limiters"—hard boundaries like "can't handle non-linear timelines" or "avoids ambiguous endings." An AI chatbot should capture these early and treat them as seriously as positive preferences.

## Design principles for an AI bookstore chatbot

The research converges on several actionable insights for chatbot design:

**Model the reader's advisory conversation.** Start with open questions ("What's a book you really enjoyed recently?"), probe for appeal factors ("What drew you to that one?"), and explicitly ask about dislikes. Don't demand perfect input—help users articulate preferences through dialogue. The Brooklyn librarian's insight applies: "Why you may like a particular book and why someone else likes the same book may be for totally different reasons."

**Capture multi-dimensional preferences.** Move beyond genre to include mood (adventurous/contemplative/dark/hopeful), pacing (fast/slow/builds tension), focus (character-driven/plot-driven/setting-rich), and hard limits (content to avoid, deal-breakers). StoryGraph's success proves richer preference capture enables dramatically better matching.

**Embrace "I don't know."** When users can't articulate preferences, offer comparative choices ("Would you prefer something that moves quickly or lets you sink into the atmosphere?"), suggest starting points based on partial information, or ask about other entertainment they enjoy to infer reading preferences. The vibe-based approach—"describe the feeling you want"—works when genre questions fail.

**Explain recommendations.** Users trust human recommenders partly because they explain *why*: "Based on what you said about loving the atmosphere in that book, you might like this one which has a similar dreamy quality but with more tension." Staff picks with personal explanations outperform algorithm outputs because they build trust through transparency.

**Track the right metrics.** Success isn't click-through; it's whether readers finish and enjoy recommended books. Serendipity (pleasant surprise) and diversity (range of suggestions) correlate more strongly with satisfaction than raw accuracy. Design for discovery, not just matching.

## Conclusion

The book discovery problem is uniquely difficult because what makes readers love specific books resists quantification—voice, tone, emotional resonance. The most successful approaches bridge this gap by using structured human input to capture these qualities: mood sliders, appeal factor tagging, content warning systems, and conversational preference elicitation. 

For an AI chatbot, the path forward combines librarian expertise with LLM capabilities: semantic understanding of nuanced requests, conversational context that builds over multiple exchanges, and the ability to explain recommendations in human terms. The key insight from Reddit communities is that readers *want* to have conversations about books—they just need a counterpart skilled enough to understand what they mean when they say "something that feels like autumn."