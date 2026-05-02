"""
Bedtime Stories — Ambulimama-style Indian moral tales (Panchatantra,
Jataka, Tenali Raman, Akbar-Birbal). Visibility is gated by a simple
email allowlist set via the BEDTIME_STORIES_USER_EMAILS env var
(comma-separated). Users not on the list see a 404, so the route
effectively doesn't exist for them and won't show in the nav either.
"""
import os
from flask import Blueprint, abort, render_template
from flask_login import current_user

from auth import login_required

bedtime_stories_bp = Blueprint("bedtime_stories", __name__)


def _allowlist():
    """Lowercased set of emails allowed to see Bedtime Stories. Empty
    set means feature is off for everyone — that's the safe default."""
    raw = os.environ.get("BEDTIME_STORIES_USER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def user_allowed(user=None):
    """Used by the route guard and by the context processor that hides
    the nav link. Accepts an optional user so callers don't need to
    import flask_login."""
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    email = (getattr(user, "email", "") or "").lower()
    return email in _allowlist()


# ─────────────────────── stories ────────────────────────
# Hand-written for the kid in mind: short paragraphs, simple language,
# named characters, and a one-line moral pulled out at the end. Style
# nods to the old Ambulimama monthlies — calm narrator, gentle pace.
STORIES = [
    {
        "slug": "tortoise-and-the-geese",
        "title": "The Tortoise and the Geese",
        "source": "Panchatantra",
        "body": [
            "Long ago, in a small lake at the edge of a quiet forest, there lived a "
            "tortoise named Kambugriva. He was full of stories and full of opinions, "
            "and he could not keep either to himself. His two best friends were a pair "
            "of wild geese named Sankata and Vikata.",
            "One summer the rains failed. The lake shrank, the lotus stalks wilted, and "
            "the mud cracked into dry plates. Kambugriva looked at his disappearing home "
            "and his eyes filled with tears.",
            "‘Friends,’ he said, ‘I shall not last a week here. Take me with you to your "
            "great pond beyond the hills.’",
            "The geese thought for a while. ‘We can carry you,’ they said, ‘but only if "
            "you do exactly as we say. We will hold the ends of a strong stick in our "
            "beaks. You will bite the middle of the stick. And no matter what happens — "
            "no matter who shouts at us, no matter what you see below — you must not "
            "open your mouth.’",
            "‘I promise,’ said Kambugriva.",
            "Up they went into the bright morning sky. Below, a village of children "
            "looked up and pointed and laughed. ‘Look at the foolish tortoise! Hanging "
            "from a stick like a piece of laundry!’",
            "Kambugriva’s ears burned. He wanted, more than anything in the world, to "
            "tell those rude children exactly what he thought of them. The wish grew "
            "until it was bigger than the sky.",
            "He opened his mouth — and down he fell.",
        ],
        "moral": "A wise tongue knows when to stay still. Our worst falls are often "
                 "from the height of our own pride.",
    },
    {
        "slug": "the-foolish-lion-and-the-clever-rabbit",
        "title": "The Foolish Lion and the Clever Rabbit",
        "source": "Panchatantra",
        "body": [
            "In a deep forest there ruled a lion named Bhasuraka who was so cruel that "
            "every morning he killed three or four animals just for the pleasure of it. "
            "The animals met in fear and held a long, sad meeting.",
            "‘Let us strike a bargain with the king,’ said an old deer. ‘We shall send "
            "him one animal each day, in turn, so the rest may live in peace.’",
            "Bhasuraka, lazy and pleased to have his food walk to him, agreed. And so "
            "the days passed, until the lot fell to a small rabbit named Pundarika.",
            "Pundarika walked very, very slowly. By the time he reached the lion, the "
            "sun was already high and the lion was roaring in hunger.",
            "‘Why are you late, you miserable mouthful?’ thundered Bhasuraka.",
            "‘Forgive me, your majesty,’ said Pundarika, breathless. ‘I was bringing "
            "five rabbits as your meal — but on the way, another lion stopped us. He "
            "said he was the true king of the forest. He ate the other four and sent "
            "me to fetch you.’",
            "Bhasuraka’s eyes blazed. ‘Take me to him at once!’",
            "Pundarika led the lion to a deep, still well at the edge of the forest. "
            "‘He hides inside this fort, your majesty.’",
            "Bhasuraka looked down. Far below, glaring back at him from the dark water, "
            "was another lion — angry, fierce, ready to fight. Roaring with rage, he "
            "leapt — and the forest had peace again.",
        ],
        "moral": "Strength without sense breaks itself. A small mind that thinks "
                 "carefully is mightier than a big one that does not think at all.",
    },
    {
        "slug": "tenali-raman-and-the-thieves",
        "title": "Tenali Raman and the Thieves",
        "source": "Tenali Raman",
        "body": [
            "Tenali Raman, the witty courtier of King Krishnadevaraya, lived in a "
            "modest house in Vijayanagara. One evening his wife told him that thieves "
            "had been seen in the neighbourhood. She was very afraid.",
            "‘Don’t worry,’ said Raman. ‘Tonight I shall do something about it.’",
            "After dinner he stepped into the garden, opened the lid of the well, and "
            "began to drag heavy boxes out of the storeroom. ‘Quickly! Quickly!’ he "
            "whispered loudly to his wife. ‘If we hide everything in the well, no thief "
            "will ever find our gold.’",
            "Just behind the wall, two thieves who had been watching the house grinned "
            "at each other. They waited until the lamps went out, then crept in, "
            "climbed down into the well, and began hauling up the boxes.",
            "All night they worked. By dawn the well was empty and the garden was full "
            "of boxes — and inside every box was nothing but bricks, sand and earth.",
            "When Raman opened his door in the morning, the thieves were gone, but his "
            "vegetable garden was beautifully dug up, watered, and ready for planting.",
            "‘See, my dear,’ he said to his astonished wife. ‘I told you I would do "
            "something about the thieves. They came, and they have done my gardening "
            "for free.’",
        ],
        "moral": "When you cannot match a problem with strength, match it with cleverness. "
                 "A trap built of someone’s own greed costs you nothing.",
    },
    {
        "slug": "the-monkey-and-the-crocodile",
        "title": "The Monkey and the Crocodile",
        "source": "Panchatantra",
        "body": [
            "On the bank of a wide river stood a great rose-apple tree, and in its "
            "branches lived a happy monkey named Raktamukha. Each day a crocodile named "
            "Karalamukha would swim up to rest in the shade, and the two became friends. "
            "Every evening the monkey threw down sweet apples for the crocodile to take "
            "home to his wife.",
            "Now the crocodile’s wife tasted the apples and thought wickedly: ‘If the "
            "fruit is this sweet, the heart of the monkey who eats it must be sweeter "
            "still. I want to eat his heart.’",
            "‘Bring him home for dinner,’ she said. The crocodile, foolish and fond of "
            "his wife, agreed.",
            "The next day Karalamukha invited Raktamukha onto his back and began to "
            "swim across the river. Halfway across, his courage failed him and he "
            "blurted the truth.",
            "Raktamukha’s heart pounded — but his face was still. ‘Oh dear friend!’ he "
            "said brightly. ‘Why did you not tell me before? My heart is not in my body. "
            "I leave it on a high branch of the rose-apple tree every morning. Take me "
            "back at once and I shall fetch it for you.’",
            "The crocodile, who was not very bright, swam back. The moment they "
            "touched the bank, the monkey leapt into the highest branch and laughed.",
            "‘Foolish friend! No creature keeps its heart anywhere but in its body. You "
            "have lost a friend today, and you have learned the price of trusting a "
            "wicked plan.’",
        ],
        "moral": "Quick wit is the best sword in a sudden danger. And a true friend "
                 "never carries you toward harm, even on the orders of someone they love.",
    },
    {
        "slug": "birbal-and-the-khichdi",
        "title": "Birbal and the Pot of Khichdi",
        "source": "Akbar-Birbal",
        "body": [
            "One winter morning Emperor Akbar stood at the palace window and watched "
            "the river below. The water was so cold that a thin sheet of ice had "
            "formed at the edge.",
            "‘Birbal,’ said the emperor, ‘could any man stand all night in such water?’",
            "‘He could, your majesty, if the reward was great enough,’ said Birbal.",
            "A challenge was announced. A poor washerman accepted, and that very night "
            "stood up to his neck in the freezing river until sunrise. In the morning "
            "he came to the court for his reward.",
            "‘How did you survive?’ asked Akbar.",
            "‘There was a lamp burning in the palace tower, your majesty. I kept my "
            "eyes on it all night, and the thought of its warmth gave me strength.’",
            "‘Then you cheated,’ said the emperor. ‘You took warmth from the palace lamp. "
            "No reward.’",
            "The washerman left in tears and went to Birbal’s house. The next day "
            "Birbal did not come to court. Akbar sent for him.",
            "‘I am cooking khichdi, your majesty,’ Birbal called back. ‘When it is "
            "ready, I shall come.’",
            "An hour passed. Two hours. By afternoon the emperor himself rode to "
            "Birbal’s house and found him stirring a pot — which hung from a tall pole, "
            "high above a tiny clay lamp on the ground.",
            "‘Birbal! How will the khichdi ever cook so far above the flame?’",
            "‘The same way, your majesty, that the washerman warmed himself from the "
            "lamp in your tower.’",
            "Akbar laughed, and the washerman got his reward.",
        ],
        "moral": "A fair ruler listens before judging, and a wise friend sometimes "
                 "teaches a lesson with silence and a story.",
    },
    {
        "slug": "the-brahmin-and-the-three-tricksters",
        "title": "The Brahmin and the Three Tricksters",
        "source": "Panchatantra",
        "body": [
            "A poor brahmin named Mitrasarma had performed a long ritual for a rich "
            "patron, and as his reward he was given a fine, fat goat. He hoisted the "
            "goat onto his shoulders and set off home through the forest.",
            "Three tricksters saw him coming. ‘That goat will feed us for a week,’ they "
            "whispered, ‘if only we can take it from the old fool.’",
            "They hid behind separate trees along the road. As the brahmin passed the "
            "first tree, the first trickster stepped out. ‘Holy sir! Why do you carry a "
            "filthy dog on your shoulders?’",
            "‘This is no dog,’ said Mitrasarma, ‘it is a goat for the gods.’",
            "‘As you wish,’ the trickster shrugged, and walked on.",
            "A little further, the second trickster appeared. ‘Holy sir, surely you "
            "know it is a sin for a brahmin to carry a dead calf?’",
            "Mitrasarma stopped. He looked at the goat. It still looked like a goat to "
            "him, but two strangers cannot both be wrong, surely?",
            "Round the next bend the third trickster bowed. ‘Holy sir, please put down "
            "that donkey before someone sees you.’",
            "Mitrasarma’s face went pale. ‘Three men have said three different things — "
            "but each was certain. I must be bewitched. Let the creature go!’",
            "He set the goat down and ran home. The three tricksters had a feast that "
            "night.",
        ],
        "moral": "Trust your own eyes more than the loud voices of strangers. A lie "
                 "repeated three times is still a lie.",
    },
    {
        "slug": "the-blue-jackal",
        "title": "The Blue Jackal",
        "source": "Panchatantra",
        "body": [
            "There was once a hungry jackal named Chandarava who wandered into a town "
            "in search of food. The town dogs chased him, snapping and barking, and in "
            "his terror he leapt over a wall and fell straight into a great vat of "
            "indigo dye.",
            "When he climbed out, his fur was the deep blue of a summer twilight. The "
            "dogs took one look at him and fled.",
            "Chandarava ran back to the forest. There, the lions and tigers and wolves "
            "stared at this strange creature in awe.",
            "‘I am Kakudruma,’ he announced grandly, ‘a god sent down by Indra himself "
            "to rule this forest.’",
            "And so they made him their king. He ate the best food, slept in the "
            "softest places, and ordered even the lion to fetch his water. He even sent "
            "his old jackal friends away — ‘they are mere jackals,’ he said, ‘they have "
            "nothing in common with me.’",
            "One night, far in the forest, a pack of jackals lifted their heads to the "
            "moon and howled, as jackals will. Chandarava, who had not howled in months, "
            "felt the cry rise in his throat.",
            "He howled.",
            "The lion blinked. The tiger blinked. ‘That,’ said the wolf slowly, ‘is the "
            "voice of a jackal.’",
            "And in the next moment they were upon him.",
        ],
        "moral": "You may paint over your nature, but you cannot silence it. Pretending "
                 "to be greater than you are will always end in your own howl.",
    },
    {
        "slug": "the-cowherd-boy-and-the-tiger",
        "title": "The Cowherd Boy and the Tiger",
        "source": "Indian folk tale",
        "body": [
            "On the edge of a village near the foot of the hills, a young cowherd named "
            "Murali grazed the village cows each day in the meadow above the stream. "
            "Murali was a good boy, but he was bored, and he loved to make the village "
            "run.",
            "One afternoon he climbed a tree and shouted: ‘Tiger! Tiger! A tiger is "
            "eating the cows!’",
            "The whole village came pounding up the path with sticks and stones — only "
            "to find Murali in the tree, laughing, and the cows chewing grass without "
            "a care. The villagers grumbled and walked back.",
            "A few days later he did it again. ‘Tiger! Tiger!’ Up they came, panting, "
            "and again there was no tiger. ‘Boy,’ said the headman sternly, ‘the next "
            "time you call us, you had better mean it.’",
            "A week passed. Murali was lying on his back chewing a grass stalk when he "
            "heard a deep, soft rumble in the bushes. He sat up. Two yellow eyes were "
            "watching him.",
            "‘TIGER!’ he screamed. ‘TIGER! IT IS TRUE!’",
            "Down in the village, the women shook their heads. ‘Let him cry,’ they "
            "said. ‘He is only making fools of us again.’",
            "When evening came and the cows wandered home alone, the village finally "
            "climbed the hill. They found the meadow empty. Murali never told a lie "
            "again — but only because he was never quite the same boy after that day.",
        ],
        "moral": "Truth is a thread you can break only so many times before no one "
                 "will hold the other end. Guard it from the start.",
    },
    {
        "slug": "the-hermit-and-the-mouse",
        "title": "The Hermit and the Little Mouse",
        "source": "Panchatantra",
        "body": [
            "On the bank of the river Ganga lived a kind hermit named Mahatapas. One "
            "day, while he sat in meditation, a hawk dropped a tiny mouse-pup at his "
            "feet and flew away. The hermit took the trembling creature home.",
            "By the power of his prayers he turned it into a little girl, and he and "
            "his wife raised her as their own daughter.",
            "When she grew up, the hermit said, ‘It is time to find you a husband. I "
            "shall give you to the greatest being in all the world.’",
            "He called the Sun. ‘Lord Sun, will you marry my daughter?’",
            "‘Ask me only,’ said the Sun, ‘if she will accept one greater than I — and "
            "the Cloud is greater, for the Cloud can hide me.’",
            "The hermit called the Cloud. ‘Marry my daughter.’ The Cloud laughed. ‘Ask "
            "the Wind. The Wind blows me wherever it pleases.’",
            "He called the Wind. The Wind said, ‘Ask the Mountain — the Mountain stops "
            "me dead.’",
            "He called the Mountain. The Mountain rumbled, ‘Ask the Mouse. The mice "
            "of the field gnaw holes in my flanks until I am crumbling.’",
            "The hermit smiled and turned to his daughter. ‘And what do you say, my "
            "child?’",
            "The girl looked at the little mouse standing at the foot of the mountain. "
            "Her eyes filled with a light he had never seen before. ‘Father,’ she "
            "whispered, ‘turn me back. I want to go home.’",
            "And so he did, and she ran joyfully into the field with the little mouse, "
            "and lived a long happy life as a mouse herself.",
        ],
        "moral": "True belonging is greater than borrowed greatness. The heart knows "
                 "where it came from, and that is where it is happiest.",
    },
]

# Slug → story dict for fast lookup. Built once at import time.
STORIES_BY_SLUG = {s["slug"]: s for s in STORIES}


# ─────────────────────── routes ────────────────────────
@bedtime_stories_bp.route("/bedtime-stories", methods=["GET"])
@login_required
def stories_index():
    """List of all bedtime stories. 404 for users not on the allowlist
    so the feature is invisible to anyone who isn't supposed to see it."""
    if not user_allowed():
        abort(404)
    return render_template(
        "bedtime_stories.html",
        stories=STORIES,
    )


@bedtime_stories_bp.route("/bedtime-stories/<slug>", methods=["GET"])
@login_required
def story_detail(slug):
    if not user_allowed():
        abort(404)
    story = STORIES_BY_SLUG.get(slug)
    if not story:
        abort(404)
    # Adjacent-story links so a child can tap "next" without going back
    # to the index.
    idx = next((i for i, s in enumerate(STORIES) if s["slug"] == slug), 0)
    prev_story = STORIES[idx - 1] if idx > 0 else None
    next_story = STORIES[idx + 1] if idx + 1 < len(STORIES) else None
    return render_template(
        "bedtime_story.html",
        story=story,
        prev_story=prev_story,
        next_story=next_story,
    )
