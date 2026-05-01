# src/vision/sentence_processor.py
"""
Letter-by-letter word builder with NLP autocomplete and name detection.

DICTIONARY
----------
Uses NLTK's 'words' corpus — 236,736 English words loaded once at
startup into a Python set.  Set lookup is O(1) so there is zero
per-query overhead regardless of dictionary size.  Loading takes
~0.3 seconds on first import, then stays in memory.

AUTOCOMPLETE
------------
1. NLTK words corpus (236k words)  — broadest coverage, offline
2. Common-words list (~600 words)  — sorted by frequency, shown first
Suggestions are ranked: shorter words first, then alphabetically.
Autocomplete is disabled when the current word is detected as a name.

NAME DETECTION
--------------
A word is flagged as a proper noun / name when:
1. It matches a known name / place in _KNOWN_NAMES, OR
2. It is 3+ letters long and NOT found in the English dictionary
   (unrecognised words → assumed to be a name or abbreviation)
When flagged, autocomplete turns off and the user spells freely.
"""

# ── NLTK setup ────────────────────────────────────────────────────────────────
try:
    import nltk
    from nltk.corpus import words as _nltk_words
    _NLTK_AVAILABLE = True
    for _c in ("words", "wordnet", "omw-1.4"):
        try:
            nltk.data.find(f"corpora/{_c}")
        except LookupError:
            print(f"📥 Downloading NLTK corpus '{_c}'…")
            nltk.download(_c, quiet=True)
except ImportError:
    _NLTK_AVAILABLE = False
    print("⚠️  NLTK not installed — using built-in word list only.")
    print("   Run: pip install nltk")

# ── Frequency-ranked common words (~600) ──────────────────────────────────────
# Listed roughly most-common-first so short suggestions appear at the top.
_FREQ_WORDS = [
    "the","be","to","of","and","a","in","that","have","it","for","not","on",
    "with","he","as","you","do","at","this","but","his","by","from","they",
    "we","say","her","she","or","an","will","my","one","all","would","there",
    "their","what","so","up","out","if","about","who","get","which","go","me",
    "when","make","can","like","time","no","just","him","know","take","people",
    "into","year","your","good","some","could","them","see","other","than",
    "then","now","look","only","come","its","over","think","also","back",
    "after","use","two","how","our","work","first","well","way","even","new",
    "want","because","any","these","give","day","most","us","great","between",
    "need","large","often","hand","high","place","hold","real","life","few",
    "north","open","seem","together","next","white","children","begin","got",
    "walk","example","ease","paper","always","music","those","both","mark",
    "book","letter","until","mile","river","car","feet","care","second","group",
    "carry","take","state","once","book","hear","stop","without","late","miss",
    "idea","enough","eat","face","watch","far","indian","real","almost","let",
    "above","girl","sometimes","mountain","cut","young","talk","soon","list",
    "song","leave","family","body","side","drive","buy","grow","human","cover",
    "color","food","sun","four","between","state","keep","eye","never","last",
    "door","example","more","cause","city","feel","race","ask","blue","red",
    "green","black","white","small","large","big","long","short","old","new",
    "right","left","early","late","hard","easy","light","heavy","fast","slow",
    "hot","cold","warm","cool","full","empty","open","close","happy","sad",
    "good","bad","great","little","high","low","strong","weak","rich","poor",
    "safe","danger","help","please","sorry","thank","hello","goodbye","yes",
    "no","okay","maybe","never","always","sometimes","often","usually","again",
    "still","already","yet","just","only","also","even","both","either","each",
    "every","another","same","different","other","such","own","few","more",
    "most","much","many","less","least","enough","able","about","above","after",
    "against","along","among","around","before","behind","below","beside",
    "between","during","except","inside","near","outside","over","past",
    "since","through","throughout","under","until","upon","within","without",
    "doctor","hospital","police","emergency","water","food","medicine","phone",
    "home","school","work","family","friend","name","mother","father","sister",
    "brother","child","baby","man","woman","person","people","country","city",
    "street","house","room","door","window","table","chair","bed","floor",
    "bathroom","kitchen","garden","road","park","shop","market","station",
    "airport","hotel","restaurant","school","office","bank","church","mosque",
    "temple","library","museum","hospital","pharmacy","police","fire",
]

# ── Known proper nouns ────────────────────────────────────────────────────────
_KNOWN_NAMES = {
    # Indian names
    "aarav","aditya","akash","amit","ananya","anjali","ankit","ankita",
    "ansh","arjun","aryan","ayaan","deepak","deepika","dev","diya","divya",
    "gaurav","ishaan","isha","kabir","kavya","kiara","krishna","manav",
    "meera","mihir","mohan","naman","neha","nikhil","nilesh","nisha","om",
    "pari","pooja","prachi","prateek","priya","rahul","raj","rajesh","riya",
    "rohit","rohan","ruchi","sahil","sanaya","sanjay","sara","saurabh",
    "shivam","shreya","shubham","simran","sneha","soham","suresh","tanvi",
    "tanya","tushar","uday","varun","vikas","vikram","vishal","vivek","yash",
    # International names
    "adam","alex","alice","andrew","anna","ben","charlie","chris","david",
    "emily","emma","ethan","grace","hannah","jack","james","jessica","john",
    "julia","kevin","liam","lily","lucas","lucy","mark","mary","max","mia",
    "michael","noah","olivia","peter","ryan","sarah","sophia","thomas",
    "william","zoe",
    # Indian cities / states
    "kolkata","mumbai","delhi","bengaluru","hyderabad","chennai","pune",
    "ahmedabad","jaipur","lucknow","patna","bhopal","indore","nagpur",
    "surat","vadodara","agra","varanasi","amritsar","chandigarh","goa",
    "kerala","gujarat","rajasthan","maharashtra","karnataka","bengal",
    # International cities / countries
    "india","london","paris","tokyo","dubai","singapore","newyork",
    "sydney","berlin","moscow","beijing","bangkok","toronto","washington",
    "america","england","france","germany","japan","china","australia",
    "canada","russia","italy","spain","brazil","mexico","pakistan",
}


# ── Build full dictionary set (loaded ONCE at module import) ──────────────────
def _build_word_set() -> set:
    """
    Load NLTK's full English word list (236,736 words) into a set.
    Set membership test is O(1) — no slowdown regardless of size.
    Falls back to _FREQ_WORDS if NLTK is unavailable.
    """
    ws = set(w.lower() for w in _FREQ_WORDS)
    if _NLTK_AVAILABLE:
        try:
            nltk_ws = set(w.lower() for w in _nltk_words.words())
            ws |= nltk_ws
            print(f"✅ Dictionary loaded: {len(ws):,} English words.")
        except Exception as e:
            print(f"⚠️  Could not load NLTK word corpus: {e}")
            print("   Using built-in list only.")
    else:
        print(f"ℹ️  Using built-in word list ({len(ws)} words).")
    return ws

# Load once at import time (~0.3 sec, then stays in memory)
_WORD_SET: set = _build_word_set()


# ═════════════════════════════════════════════════════════════════════════════
# LETTER BUFFER
# ═════════════════════════════════════════════════════════════════════════════

class LetterBuffer:
    """
    Accumulates signed letters → builds words → builds sentences.

    Key methods
    -----------
    add_letter(letter)          → add one signed letter, returns state dict
    delete_last_letter()        → backspace
    confirm_word(override="")   → finalise current word
    confirm_suggestion(word)    → accept autocomplete suggestion
    delete_last_word()          → undo last completed word
    clear_all()                 → reset everything
    get_suggestions()           → autocomplete list
    get_sentence()              → formatted sentence string
    """

    def __init__(self):
        self.current_letters: list[str] = []
        self.sentence_words:  list[str] = []
        self.is_name:         bool      = False

    # ── Letter input ──────────────────────────────────────────────────────────

    def add_letter(self, letter: str) -> dict:
        letter = letter.upper().strip()
        if not letter or not letter.isalpha():
            return self._state()
        self.current_letters.append(letter)
        self.is_name = self._detect_name("".join(self.current_letters))
        return self._state()

    def delete_last_letter(self) -> dict:
        if self.current_letters:
            self.current_letters.pop()
        self.is_name = self._detect_name("".join(self.current_letters))
        return self._state()

    def confirm_word(self, override_word: str = "") -> dict:
        word = override_word if override_word else "".join(self.current_letters)
        if word:
            stored = word.capitalize() if self.is_name else word.lower()
            self.sentence_words.append(stored)
        self.current_letters = []
        self.is_name         = False
        return self._state()

    def confirm_suggestion(self, suggestion: str) -> dict:
        return self.confirm_word(override_word=suggestion)

    def delete_last_word(self) -> dict:
        if self.sentence_words:
            self.sentence_words.pop()
        return self._state()

    def clear_all(self) -> dict:
        self.current_letters = []
        self.sentence_words  = []
        self.is_name         = False
        return self._state()

    # ── Name detection ────────────────────────────────────────────────────────

    def _detect_name(self, word: str) -> bool:
        """
        Return True if word looks like a proper noun / name.
        Autocomplete is disabled when this returns True.

        Uses the full 236k-word NLTK dictionary for reliable detection.
        An unrecognised word of 3+ letters → assumed to be a name.
        """
        if not word:
            return False
        lower = word.lower()
        if lower in _KNOWN_NAMES:
            return True
        # Not in the full English dictionary → likely a name
        if len(lower) >= 3 and lower not in _WORD_SET:
            return True
        return False

    # ── Autocomplete ──────────────────────────────────────────────────────────

    def get_suggestions(self, max_results: int = 4) -> list[str]:
        """
        Return up to max_results autocomplete suggestions for current prefix.

        Disabled (returns []) when:
        - is_name is True
        - Buffer has < 2 letters
        """
        if self.is_name or len(self.current_letters) < 2:
            return []

        prefix = "".join(self.current_letters).lower()
        found  = []

        # Pass 1: frequency-ranked common words (appear first in suggestions)
        for word in _FREQ_WORDS:
            if word.startswith(prefix) and word != prefix:
                found.append(word)

        # Pass 2: full NLTK dictionary (236k words)
        for word in _WORD_SET:
            if word.startswith(prefix) and word != prefix and word not in found:
                found.append(word)
            # Early exit once we have plenty of candidates
            if len(found) >= max_results * 8:
                break

        # Sort: prefer shorter words, then alphabetically
        found.sort(key=lambda w: (len(w), w))

        # Deduplicate preserving order
        seen   = set()
        unique = []
        for w in found:
            if w not in seen:
                seen.add(w)
                unique.append(w)

        return unique[:max_results]

    # ── Sentence formatting ───────────────────────────────────────────────────

    def get_sentence(self) -> str:
        if not self.sentence_words:
            return ""
        words    = list(self.sentence_words)
        words[0] = words[0].capitalize()
        sentence = " ".join(words)
        if sentence[-1] not in ".!?":
            q_starts = {"what","where","when","why","how","who","is","are","can","do","did"}
            urgent   = {"help","emergency","danger","stop","fire","call","police"}
            if words[0].lower() in q_starts:
                sentence += "?"
            elif any(w.lower() in urgent for w in words):
                sentence += "!"
            else:
                sentence += "."
        return sentence

    # ── State dict ────────────────────────────────────────────────────────────

    def _state(self) -> dict:
        return {
            "current_word": "".join(self.current_letters),
            "suggestions":  self.get_suggestions(),
            "is_name":      self.is_name,
            "sentence":     self.get_sentence(),
            "word_count":   len(self.sentence_words),
        }


# ── Backwards-compatible wrapper ──────────────────────────────────────────────

class SignLanguageNLP:
    """Backwards-compatible wrapper. New code should use LetterBuffer directly."""

    def __init__(self):
        self.buffer = LetterBuffer()

    def process_sentence(self, word_sequence: list) -> str:
        if not word_sequence:
            return ""
        if isinstance(word_sequence, str):
            word_sequence = [word_sequence]
        words    = [w.replace("_", " ") for w in word_sequence]
        sentence = " ".join(words).strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        return sentence + "." if sentence and sentence[-1] not in ".!?" else sentence

    def suggest_next_words(self, current_sequence: list) -> list:
        defaults = {
            "i":    ["want","need","am","can"],
            "you":  ["are","can","want"],
            "help": ["me","please","emergency"],
            "need": ["help","doctor","water"],
        }
        last = current_sequence[-1].lower() if current_sequence else ""
        return defaults.get(last, ["please","thank","yes","no"])

    def correct_spelling(self, word: str) -> str:
        lower = word.lower()
        return lower if lower in _WORD_SET else word

    def expand_sentence(self, words: list) -> str:
        expansions = {
            "hello": "Hello! How can I help you?",
            "help":  "I need help! Please assist me.",
            "thank": "Thank you very much!",
            "sorry": "I am sorry about that.",
            "yes":   "Yes, that is correct.",
            "no":    "No, that is not right.",
        }
        if len(words) <= 2 and words:
            if words[0].lower() in expansions:
                return expansions[words[0].lower()]
        return self.process_sentence(words)