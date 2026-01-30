# The book data landscape for semantic search: A comprehensive guide

**Building semantic search over modern books faces a fundamental paradox**: legal datasets offer extensive metadata and descriptions for millions of titles, but full-text access to post-2000 copyrighted works remains essentially unavailable through legitimate channels. Shadow libraries, by contrast, index over 60 million books with full text—but their use carries significant legal risk. This report maps the complete terrain to help navigate these trade-offs.

The most practical path for modern book semantic search combines the **UCSD Book Graph** (2.36 million books with Goodreads descriptions), **Amazon Reviews 2023** (4.4 million book items with product descriptions), and **Google Books API** (40+ million titles indexed with variable description quality). For full-text analysis of modern works, no legal bulk option exists—this represents the core gap between what's technically possible and what's legally accessible.

## Legal datasets with meaningful description coverage

### UCSD Book Graph leads for modern book metadata
The **UCSD Book Graph** (mengtingwan.github.io/data/goodreads.html) stands as the most valuable dataset for modern book descriptions and metadata. Scraped from Goodreads in late 2017, it contains **2.36 million books** with full descriptions, 229 million user-book interactions, and 15+ million detailed reviews. Crucially, it includes substantial post-2000 coverage since Goodreads catalogs actively-read contemporary books.

Data fields include title, description, publisher, publication year, ISBNs, average ratings, popular shelves (user-generated genre tags), series information, and similar books lists. Access is via direct wget download (~2GB compressed), restricted to academic use only with proper citation. Genre-specific subsets are available (Romance: 335K books; Fantasy: 258K books).

### Amazon Reviews 2023 offers the freshest data
The **Amazon Reviews 2023** dataset from UCSD's McAuley Lab provides the most current commercial book metadata: **29.5 million book reviews** from 10.3 million users across **4.4 million items**, spanning May 1996 through September 2023. Product metadata includes descriptions, features (bullet points), categories, and pricing.

Available via HuggingFace (`McAuley-Lab/Amazon-Reviews-2023`) or direct download, this dataset captures the full scope of Amazon's book marketplace. An older AWS version (`amazon-reviews-pds` S3 bucket) offers 130+ million reviews across categories in TSV format. Both versions restrict use to academic research.

### CMU Book Summary provides Wikipedia-sourced plot summaries
The **CMU Book Summary Dataset** offers **16,559 books** with plot summaries extracted from Wikipedia, including title, author, genre classifications from Freebase, and Wikipedia/Freebase IDs. At ~17MB compressed, it's lightweight but useful for genre classification and NLP tasks. Modern bestsellers with Wikipedia articles are included.

Access: cs.cmu.edu/~dbamman/booksummaries.html or Kaggle/HuggingFace mirrors.

### The full-text gap remains legally unbridgeable
**BookCorpus** (7,185 unique books, ~985 million words) was foundational for training BERT and GPT but faces severe availability issues. Originally scraped from Smashwords' free ebooks, the dataset is no longer officially distributed. A 2021 analysis by Bandy & Vincent documented copyright violations—over 200 books explicitly prohibit reproduction, and 406 titles that were free now cost money. Unofficial copies exist but carry legal risk.

For legal full text, only public domain options exist:
- **Project Gutenberg/SPGC**: 50,000+ pre-1928 works, 3+ billion tokens
- **BookSum** (Salesforce): 217 classic titles with chapter-level summaries from study guides
- **HathiTrust**: 18+ million digitized volumes, but copyrighted works are search-only with no reading access

## APIs and services for book data access

### Google Books API provides the broadest coverage
**Google Books API** offers the best combination of coverage and description quality for modern books. With **40+ million titles indexed**, it provides metadata, descriptions (variable length—from brief to full publisher flap copy), cover images, ratings, and preview text where publishers allow.

| Specification | Details |
|---------------|---------|
| Rate limit | 1,000 requests/day (increases available on request) |
| Authentication | API key required (free via Google Cloud Console) |
| Description quality | Variable; publisher-provided descriptions tend to be detailed |
| Full text | Public domain only; previews depend on publisher agreements |
| Bulk access | Not supported; designed for real-time queries |

Key limitation: Terms of service prohibit permanent storage for commercial use. Descriptions must be attributed when displayed.

### Open Library enables free bulk access
**Open Library** (Internet Archive) catalogs **30+ million editions** with free API access and monthly bulk data dumps (~250GB total). No API key required for read operations.

Strengths include freely redistributable metadata under CC0 license and Controlled Digital Lending for ~1.4 million modern copyrighted books (though this faces ongoing legal challenges from publishers). Weaknesses: description coverage is inconsistent and community-sourced.

Bulk dumps available at openlibrary.org/developers/dumps—the only free source for large-scale book metadata collection.

### ISBNdb requires paid subscription but offers depth
**ISBNdb** claims **106+ million book records** with up to 19 data points per book including synopses. Pricing starts at $14.95/month (10,000 calls/day) up to $299.95/month for unlimited access and custom data dumps. Academic discounts available.

Best for: filling coverage gaps, accessing bibliographic data at scale, commercial applications where Google Books ToS restrictions apply.

### Goodreads API is deprecated—Hardcover emerges as alternative
Goodreads deprecated its API in December 2020 and no longer issues developer keys. **Hardcover** (hardcover.app) has emerged as a community-driven alternative with a free GraphQL API offering book metadata, ratings, reviews, and user bookshelves at 60 requests/minute. Database is growing but smaller than Goodreads' historical scale.

### Other notable APIs
- **OCLC/WorldCat**: Billions of bibliographic records, but requires institutional membership
- **Penguin Random House API**: Free access to PRH catalog with good flap copy descriptions—limited to one publisher group
- **New York Times Books API**: Best-seller lists and reviews only (1,000 requests/day free)
- **LibraryThing**: Limited to 1,000 requests/day, JSON APIs restricted to browser-side JavaScript only

## Shadow libraries: scale and coverage for context

Understanding the shadow library landscape helps contextualize the coverage gaps in legal sources—this section draws from academic studies and published statistics.

### Anna's Archive now indexes the largest collection
**Anna's Archive**, founded November 2022 after the Z-Library seizure, has become the dominant meta-index for shadow library content. Current statistics:

- **61.6 million books indexed**
- **95.7 million papers indexed** 
- **~1.1 petabytes** total torrent size

It aggregates multiple sources: Library Genesis (7.6M files), Z-Library mirrors (21.6M items), Sci-Hub (95.5M papers), plus Internet Archive controlled collections and WorldCat metadata (scraped in October 2023). The platform faces ongoing legal action—OCLC filed suit in January 2024 over the WorldCat scrape.

### Library Genesis remains the foundational source
**LibGen**, founded 2008 in Russia, contains:
- **2.4+ million non-fiction books**
- **2.2 million fiction books**  
- **80+ million scientific articles** (via Sci-Hub)
- **~70-100 TB** total database size

Subject coverage transformed from Russian natural sciences to predominantly English multidisciplinary content after absorbing Gigapedia (Library.nu) in 2011-2012. A 2014 analysis found only 66% of downloaded LibGen titles were available for purchase on Amazon—indicating substantial coverage of out-of-print and hard-to-find works.

LibGen faces mounting legal pressure: a September 2024 ruling ordered $30 million in damages to publishers, and December 2024 domain seizures caused significant outages.

### Z-Library claimed the largest ebook collection
Before its November 2022 seizure, **Z-Library** claimed **11-22 million ebooks** and 84 million articles, marketing itself as "the world's largest ebook library." Operators (Russian nationals) were arrested in Argentina but escaped house arrest in July 2024. The service continues via Tor and personal user domains, with content now mirrored in Anna's Archive.

### Academic research documents extensive coverage
A 2018 eLife study found **Sci-Hub covers 68.9%** of all 81.6 million scholarly articles with DOIs—rising to **85.1% for toll-access journals** and exceeding 97% for major publishers like Elsevier. This coverage surpasses what even major research universities like UPenn can access through subscriptions.

For books, no equivalent coverage study exists, but the scale differential is stark: legal datasets offer metadata for millions of books but full text for only ~60,000 public domain works, while shadow libraries provide full text for 60+ million titles including contemporary publications.

## Comparative analysis for semantic search applications

### Where legal sources suffice
For applications needing **book descriptions, synopses, and metadata** for modern books, legal sources provide adequate coverage:

| Source | Books | Description Quality | Access Model |
|--------|-------|---------------------|--------------|
| UCSD Book Graph | 2.36M | Good (Goodreads descriptions) | Free, academic |
| Amazon Reviews 2023 | 4.4M items | Good (product descriptions) | Free, academic |
| Google Books API | 40M+ | Variable (publisher-dependent) | Free API, no bulk |
| Open Library dumps | 30M+ editions | Inconsistent | Free, CC0 |
| CMU Book Summary | 16.5K | Good (Wikipedia plots) | Free |

Combined, these sources can support robust semantic search over book descriptions, reviews, and metadata—sufficient for recommendation systems, genre classification, and discovery interfaces.

### Where legal sources fall short
For applications requiring **full text of modern books**—including semantic search over book contents, chapter-level analysis, or quote extraction—legal options are essentially non-existent:

- **Full-text legal sources** (Gutenberg, BookSum) contain only pre-1928 public domain works
- **BookCorpus** has copyright issues and is no longer officially distributed
- **Open Library's Controlled Digital Lending** provides loan access but no bulk text extraction
- **HathiTrust** allows only non-consumptive computational research for copyrighted works

Shadow libraries fill this gap with **60+ million full-text books including modern titles**, but use violates copyright law in most jurisdictions and carries legal and ethical risks.

### The coverage comparison makes the gap clear
For a typical query about post-2000 bestsellers:
- **Legal metadata sources**: Strong coverage of titles, authors, descriptions, reviews
- **Legal full-text sources**: Near-zero coverage (unless public domain or purchased individually)
- **Shadow libraries**: Estimated 80%+ coverage of commercially published books

### Practical recommendations by use case

**For semantic search over descriptions/metadata (legally feasible):**
1. Start with UCSD Book Graph for Goodreads descriptions
2. Supplement with Amazon Reviews 2023 for product descriptions and reviews
3. Use Google Books API for real-time lookups and gap-filling
4. Consider Open Library bulk dumps for complete bibliographic coverage

**For full-text analysis (legally constrained):**
- Public domain works: Use Standardized Project Gutenberg Corpus (50K+ books)
- Modern works: No legal bulk option exists; consider Open Library's lending program for individual access, or HathiTrust Research Center for non-consumptive research partnerships

**For commercial applications:**
- Google Books ToS prohibits permanent storage; use ISBNdb or negotiate direct publisher agreements
- Open Library metadata (CC0) can be freely redistributed
- UCSD/Amazon datasets explicitly restrict commercial use

## Conclusion

The book data landscape bifurcates sharply between metadata abundance and full-text scarcity for modern works. Legal datasets from UCSD, Amazon, and Google provide rich descriptions, reviews, and metadata covering millions of post-2000 titles—sufficient for many semantic search applications. But full-text access to copyrighted books remains locked behind copyright, with shadow libraries offering the only comprehensive alternative at significant legal risk.

For practitioners building book discovery systems, the pragmatic approach combines **UCSD Book Graph** (descriptions), **Amazon Reviews 2023** (reviews and product data), and **Google Books API** (real-time lookups)—yielding coverage of several million modern titles with meaningful text for embedding and search. Full-text semantic search over modern book contents, however, awaits either legal reform, new licensing models, or publisher partnerships that don't yet exist at scale.