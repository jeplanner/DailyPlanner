"""
Idempotent upsert of the bedtime-stories corpus into Supabase.

Run from the repo root:

    python3 scripts/seed_bedtime_stories.py

Re-running is safe — rows are upserted by slug, so editing a story or
adding new ones to CORPUS just keeps the DB in sync. Requires the
table created by MIGRATION_BEDTIME_STORIES.sql and SUPABASE_URL +
SUPABASE_KEY in the environment.

Add new stories at the end of CORPUS with a unique slug — the route's
list view is paginated so the corpus can grow indefinitely.
"""
import os
import sys

# Allow running from repo root without an installed package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import _session, SUPABASE_URL, HEADERS  # noqa: E402


def _p(*paragraphs):
    """Tiny helper so the corpus literal stays readable: each paragraph
    on its own argument, joined with a blank line as the route expects."""
    return "\n\n".join(paragraphs)


# ─────────────────────── corpus ────────────────────────
# Each entry: slug (kebab-case, unique), source, title, body, moral,
# sort_order. sort_order drives display order in the index. Stories
# from the same tradition tend to be grouped together for filtering.
CORPUS = [
    # ── Panchatantra & Indian classics (1-20) ──────────────
    {
        "slug": "tortoise-and-the-geese",
        "source": "Panchatantra",
        "title": "The Tortoise and the Geese",
        "body": _p(
            "Long ago, in a small lake at the edge of a quiet forest, there lived a tortoise named Kambugriva. He was full of stories and full of opinions, and he could not keep either to himself. His two best friends were a pair of wild geese named Sankata and Vikata.",
            "One summer the rains failed. The lake shrank, the lotus stalks wilted, and the mud cracked into dry plates. Kambugriva looked at his disappearing home and his eyes filled with tears.",
            "‘Friends,’ he said, ‘I shall not last a week here. Take me with you to your great pond beyond the hills.’",
            "The geese thought for a while. ‘We can carry you,’ they said, ‘but only if you do exactly as we say. We will hold the ends of a strong stick in our beaks. You will bite the middle of the stick. And no matter what happens — no matter who shouts at us, no matter what you see below — you must not open your mouth.’",
            "‘I promise,’ said Kambugriva.",
            "Up they went into the bright morning sky. Below, a village of children looked up and pointed and laughed. ‘Look at the foolish tortoise! Hanging from a stick like a piece of laundry!’",
            "Kambugriva’s ears burned. He wanted, more than anything in the world, to tell those rude children exactly what he thought of them. The wish grew until it was bigger than the sky. He opened his mouth — and down he fell.",
        ),
        "moral": "A wise tongue knows when to stay still. Our worst falls are often from the height of our own pride.",
        "sort_order": 1,
    },
    {
        "slug": "the-foolish-lion-and-the-clever-rabbit",
        "source": "Panchatantra",
        "title": "The Foolish Lion and the Clever Rabbit",
        "body": _p(
            "In a deep forest there ruled a lion named Bhasuraka who was so cruel that every morning he killed three or four animals just for the pleasure of it. The animals met in fear and held a long, sad meeting.",
            "‘Let us strike a bargain with the king,’ said an old deer. ‘We shall send him one animal each day, in turn, so the rest may live in peace.’",
            "Bhasuraka, lazy and pleased to have his food walk to him, agreed. And so the days passed, until the lot fell to a small rabbit named Pundarika.",
            "Pundarika walked very, very slowly. By the time he reached the lion, the sun was already high and the lion was roaring in hunger. ‘Why are you late, you miserable mouthful?’ thundered Bhasuraka.",
            "‘Forgive me, your majesty,’ said Pundarika, breathless. ‘I was bringing five rabbits as your meal — but on the way, another lion stopped us. He said he was the true king of the forest. He ate the other four and sent me to fetch you.’",
            "Bhasuraka’s eyes blazed. ‘Take me to him at once!’ Pundarika led the lion to a deep, still well at the edge of the forest. ‘He hides inside this fort, your majesty.’",
            "Bhasuraka looked down. Far below, glaring back at him from the dark water, was another lion — angry, fierce, ready to fight. Roaring with rage, he leapt — and the forest had peace again.",
        ),
        "moral": "Strength without sense breaks itself. A small mind that thinks carefully is mightier than a big one that does not think at all.",
        "sort_order": 2,
    },
    {
        "slug": "tenali-raman-and-the-thieves",
        "source": "Tenali Raman",
        "title": "Tenali Raman and the Thieves",
        "body": _p(
            "Tenali Raman, the witty courtier of King Krishnadevaraya, lived in a modest house in Vijayanagara. One evening his wife told him that thieves had been seen in the neighbourhood. She was very afraid.",
            "‘Don’t worry,’ said Raman. ‘Tonight I shall do something about it.’",
            "After dinner he stepped into the garden, opened the lid of the well, and began to drag heavy boxes out of the storeroom. ‘Quickly! Quickly!’ he whispered loudly to his wife. ‘If we hide everything in the well, no thief will ever find our gold.’",
            "Just behind the wall, two thieves who had been watching the house grinned at each other. They waited until the lamps went out, then crept in, climbed down into the well, and began hauling up the boxes.",
            "All night they worked. By dawn the well was empty and the garden was full of boxes — and inside every box was nothing but bricks, sand and earth.",
            "When Raman opened his door in the morning, the thieves were gone, but his vegetable garden was beautifully dug up, watered, and ready for planting. ‘See, my dear,’ he said. ‘I told you I would do something about the thieves. They have done my gardening for free.’",
        ),
        "moral": "When you cannot match a problem with strength, match it with cleverness. A trap built of someone’s own greed costs you nothing.",
        "sort_order": 3,
    },
    {
        "slug": "the-monkey-and-the-crocodile",
        "source": "Panchatantra",
        "title": "The Monkey and the Crocodile",
        "body": _p(
            "On the bank of a wide river stood a great rose-apple tree, and in its branches lived a happy monkey named Raktamukha. Each day a crocodile named Karalamukha would swim up to rest in the shade, and the two became friends. Every evening the monkey threw down sweet apples for the crocodile to take home to his wife.",
            "Now the crocodile’s wife tasted the apples and thought wickedly: ‘If the fruit is this sweet, the heart of the monkey who eats it must be sweeter still. I want to eat his heart.’ ‘Bring him home for dinner,’ she said. The crocodile, foolish and fond of his wife, agreed.",
            "The next day Karalamukha invited Raktamukha onto his back and began to swim across the river. Halfway across, his courage failed him and he blurted the truth.",
            "Raktamukha’s heart pounded — but his face was still. ‘Oh dear friend!’ he said brightly. ‘Why did you not tell me before? My heart is not in my body. I leave it on a high branch of the rose-apple tree every morning. Take me back at once and I shall fetch it for you.’",
            "The crocodile, who was not very bright, swam back. The moment they touched the bank, the monkey leapt into the highest branch and laughed. ‘Foolish friend! No creature keeps its heart anywhere but in its body. You have lost a friend today, and you have learned the price of trusting a wicked plan.’",
        ),
        "moral": "Quick wit is the best sword in a sudden danger. A true friend never carries you toward harm.",
        "sort_order": 4,
    },
    {
        "slug": "birbal-and-the-khichdi",
        "source": "Akbar-Birbal",
        "title": "Birbal and the Pot of Khichdi",
        "body": _p(
            "One winter morning Emperor Akbar stood at the palace window and watched the river below. The water was so cold that a thin sheet of ice had formed at the edge.",
            "‘Birbal,’ said the emperor, ‘could any man stand all night in such water?’ ‘He could, your majesty, if the reward was great enough,’ said Birbal.",
            "A challenge was announced. A poor washerman accepted, and that very night stood up to his neck in the freezing river until sunrise. In the morning he came to the court for his reward.",
            "‘How did you survive?’ asked Akbar. ‘There was a lamp burning in the palace tower, your majesty. I kept my eyes on it all night, and the thought of its warmth gave me strength.’ ‘Then you cheated,’ said the emperor. ‘You took warmth from the palace lamp. No reward.’",
            "The washerman left in tears and went to Birbal’s house. The next day Birbal did not come to court. Akbar sent for him. ‘I am cooking khichdi, your majesty,’ Birbal called back. ‘When it is ready, I shall come.’",
            "An hour passed. Two hours. By afternoon the emperor himself rode to Birbal’s house and found him stirring a pot — which hung from a tall pole, high above a tiny clay lamp on the ground. ‘Birbal! How will the khichdi ever cook so far above the flame?’",
            "‘The same way, your majesty, that the washerman warmed himself from the lamp in your tower.’ Akbar laughed, and the washerman got his reward.",
        ),
        "moral": "A fair ruler listens before judging, and a wise friend sometimes teaches a lesson with a story.",
        "sort_order": 5,
    },
    {
        "slug": "the-brahmin-and-the-three-tricksters",
        "source": "Panchatantra",
        "title": "The Brahmin and the Three Tricksters",
        "body": _p(
            "A poor brahmin named Mitrasarma had performed a long ritual for a rich patron, and as his reward he was given a fine, fat goat. He hoisted the goat onto his shoulders and set off home through the forest.",
            "Three tricksters saw him coming. ‘That goat will feed us for a week,’ they whispered, ‘if only we can take it from the old fool.’",
            "They hid behind separate trees along the road. As the brahmin passed the first tree, the first trickster stepped out. ‘Holy sir! Why do you carry a filthy dog on your shoulders?’ ‘This is no dog,’ said Mitrasarma, ‘it is a goat for the gods.’ ‘As you wish,’ the trickster shrugged, and walked on.",
            "A little further, the second trickster appeared. ‘Holy sir, surely you know it is a sin for a brahmin to carry a dead calf?’ Mitrasarma stopped. He looked at the goat. It still looked like a goat to him, but two strangers cannot both be wrong, surely?",
            "Round the next bend the third trickster bowed. ‘Holy sir, please put down that donkey before someone sees you.’",
            "Mitrasarma’s face went pale. ‘Three men have said three different things — but each was certain. I must be bewitched. Let the creature go!’ He set the goat down and ran home. The three tricksters had a feast that night.",
        ),
        "moral": "Trust your own eyes more than the loud voices of strangers. A lie repeated three times is still a lie.",
        "sort_order": 6,
    },
    {
        "slug": "the-blue-jackal",
        "source": "Panchatantra",
        "title": "The Blue Jackal",
        "body": _p(
            "There was once a hungry jackal named Chandarava who wandered into a town in search of food. The town dogs chased him, snapping and barking, and in his terror he leapt over a wall and fell straight into a great vat of indigo dye.",
            "When he climbed out, his fur was the deep blue of a summer twilight. The dogs took one look at him and fled.",
            "Chandarava ran back to the forest. There, the lions and tigers and wolves stared at this strange creature in awe. ‘I am Kakudruma,’ he announced grandly, ‘a god sent down by Indra himself to rule this forest.’",
            "And so they made him their king. He ate the best food, slept in the softest places, and ordered even the lion to fetch his water. He even sent his old jackal friends away — ‘they are mere jackals,’ he said, ‘they have nothing in common with me.’",
            "One night, far in the forest, a pack of jackals lifted their heads to the moon and howled, as jackals will. Chandarava, who had not howled in months, felt the cry rise in his throat. He howled.",
            "The lion blinked. The tiger blinked. ‘That,’ said the wolf slowly, ‘is the voice of a jackal.’ And in the next moment they were upon him.",
        ),
        "moral": "You may paint over your nature, but you cannot silence it. Pretending to be greater than you are will always end in your own howl.",
        "sort_order": 7,
    },
    {
        "slug": "the-cowherd-boy-and-the-tiger",
        "source": "Indian folk",
        "title": "The Cowherd Boy and the Tiger",
        "body": _p(
            "On the edge of a village near the foot of the hills, a young cowherd named Murali grazed the village cows each day in the meadow above the stream. Murali was a good boy, but he was bored, and he loved to make the village run.",
            "One afternoon he climbed a tree and shouted: ‘Tiger! Tiger! A tiger is eating the cows!’ The whole village came pounding up the path with sticks and stones — only to find Murali in the tree, laughing, and the cows chewing grass without a care. The villagers grumbled and walked back.",
            "A few days later he did it again. ‘Tiger! Tiger!’ Up they came, panting, and again there was no tiger. ‘Boy,’ said the headman sternly, ‘the next time you call us, you had better mean it.’",
            "A week passed. Murali was lying on his back chewing a grass stalk when he heard a deep, soft rumble in the bushes. He sat up. Two yellow eyes were watching him. ‘TIGER!’ he screamed. ‘TIGER! IT IS TRUE!’",
            "Down in the village, the women shook their heads. ‘Let him cry,’ they said. ‘He is only making fools of us again.’ When evening came and the cows wandered home alone, the village finally climbed the hill. They found the meadow empty.",
        ),
        "moral": "Truth is a thread you can break only so many times before no one will hold the other end.",
        "sort_order": 8,
    },
    {
        "slug": "the-hermit-and-the-mouse",
        "source": "Panchatantra",
        "title": "The Hermit and the Little Mouse",
        "body": _p(
            "On the bank of the river Ganga lived a kind hermit named Mahatapas. One day, while he sat in meditation, a hawk dropped a tiny mouse-pup at his feet and flew away. The hermit took the trembling creature home. By the power of his prayers he turned it into a little girl, and he and his wife raised her as their own daughter.",
            "When she grew up, the hermit said, ‘It is time to find you a husband. I shall give you to the greatest being in all the world.’ He called the Sun. ‘Lord Sun, will you marry my daughter?’ ‘Ask me only,’ said the Sun, ‘if she will accept one greater than I — and the Cloud is greater, for the Cloud can hide me.’",
            "He called the Cloud. The Cloud laughed. ‘Ask the Wind. The Wind blows me wherever it pleases.’ He called the Wind. The Wind said, ‘Ask the Mountain — the Mountain stops me dead.’",
            "He called the Mountain. The Mountain rumbled, ‘Ask the Mouse. The mice of the field gnaw holes in my flanks until I am crumbling.’",
            "The hermit smiled and turned to his daughter. ‘And what do you say, my child?’ The girl looked at the little mouse standing at the foot of the mountain. Her eyes filled with a light he had never seen before. ‘Father,’ she whispered, ‘turn me back. I want to go home.’ And so he did, and she ran joyfully into the field with the little mouse.",
        ),
        "moral": "True belonging is greater than borrowed greatness. The heart knows where it came from, and that is where it is happiest.",
        "sort_order": 9,
    },
    {
        "slug": "the-brahmin-and-the-mongoose",
        "source": "Panchatantra",
        "title": "The Brahmin's Wife and the Mongoose",
        "body": _p(
            "A brahmin and his wife had a baby boy, and a few days later a mongoose pup came into their house. The mother nursed the mongoose along with her child, and the two grew up like brothers, playing in the courtyard from morning to night.",
            "One day the mother had to go to the river. ‘Watch the baby,’ she said to her husband. But he wandered out to beg alms, and the cradle was left alone with the mongoose curled at its foot.",
            "While the house was empty, a black cobra slid in across the cool floor. The mongoose saw it. He fought it tooth and claw across the room, broke its neck at last, and stood panting, his face streaked with blood, the dead snake at his feet.",
            "The mother returned. The mongoose came running joyfully to greet her — his mouth red, his fur bloody. With a scream she lifted her water-pot and brought it down on his head. ‘You have eaten my child!’",
            "She rushed to the cradle. The baby slept, untouched. On the floor lay the snake. The mongoose lay still by the door.",
        ),
        "moral": "Act in haste and you will mourn at leisure. Look for the whole truth before you raise your hand.",
        "sort_order": 10,
    },
    {
        "slug": "the-mice-that-ate-iron",
        "source": "Panchatantra",
        "title": "The Mice That Ate Iron",
        "body": _p(
            "A merchant who had fallen on hard times entrusted a heavy iron balance to a friend before leaving the city to seek his fortune. ‘Keep it safe,’ he said, ‘until I return.’",
            "Months later he came back and asked for the balance. ‘Alas,’ said the friend, ‘mice have eaten it.’ ‘Mice eat iron?’ ‘In this city, yes,’ said the friend smoothly.",
            "The merchant said nothing. The next morning he asked the friend if he might take his young son to the river to bathe. The friend, pleased to be trusted, agreed.",
            "But the merchant did not bring the boy back. When the panicked friend came to ask, the merchant said gravely: ‘A great hawk swooped down and carried him off.’",
            "‘That is impossible! Hawks do not carry away grown children!’ ‘In a city where mice eat iron balances,’ said the merchant calmly, ‘a hawk can carry off a boy. Now — shall we discuss what is owed to whom?’",
        ),
        "moral": "A clever lie is best answered with an equal one. Justice sometimes wears the costume of the wrong it is correcting.",
        "sort_order": 11,
    },
    {
        "slug": "the-greedy-jackal",
        "source": "Panchatantra",
        "title": "The Greedy Jackal",
        "body": _p(
            "A hunter shot a wild boar in the forest. The boar charged, and as it died it gored the hunter. Both fell where they were.",
            "A jackal came along and stared at the feast spread before him. ‘Two fat bodies! What luck! I shall eat slowly and make this last for many days.’",
            "He looked first at the bow lying beside the hunter. ‘I shall save the meat. The bowstring is leather — a small starter.’ He sat down and gnawed the string.",
            "The bow snapped back with all its tension. The bent wood drove a splinter through the jackal’s neck.",
            "He died before he could touch a single bite of either body.",
        ),
        "moral": "Greed eats first what is small and easy, and so it never reaches the feast.",
        "sort_order": 12,
    },
    {
        "slug": "two-birds-one-body",
        "source": "Panchatantra",
        "title": "Two Birds With One Body",
        "body": _p(
            "There once was a strange bird with one body and two heads. The two heads each had their own mind, but they shared the same stomach.",
            "One day, while flying over a forest, the bird with the right head spotted a sweet, ripe fruit. ‘Wonderful!’ he said. ‘Let me eat it for both of us.’",
            "The left head was offended. ‘Why should you have all the pleasure? I want a fruit too.’ ‘But our stomach is the same,’ said the right head. ‘Whichever of us eats, we are both fed.’ The left head sulked.",
            "Soon the left head spotted a dark, bitter berry — known to be poisonous. ‘Now I shall eat,’ he said. ‘Don’t!’ cried the right. ‘It will kill us both!’ ‘You ate the sweet one alone,’ snapped the left. ‘I shall eat the bitter one alone.’",
            "He swallowed the berry. The single stomach took it in. And both heads slumped together to the ground.",
        ),
        "moral": "When two share one fate, no separate revenge is possible. To poison the other half is to poison oneself.",
        "sort_order": 13,
    },
    {
        "slug": "the-four-friends-and-the-deer",
        "source": "Panchatantra",
        "title": "Four Friends and the Deer",
        "body": _p(
            "A crow, a mouse, a tortoise and a deer were friends, and they lived around a quiet pool in the forest. They met each evening to talk and share food.",
            "One day the deer did not come. The crow flew up and at last spotted him caught in a hunter’s rope-snare, struggling and afraid. He flew back, and the four held a council.",
            "The mouse climbed onto the tortoise’s back and the tortoise lumbered to the snare. The mouse gnawed the rope through. The deer leapt free.",
            "But while they were busy, the hunter returned and saw the slow tortoise still on the path. He picked him up and put him in his bag.",
            "The deer ran out into the path and pretended to be wounded. The hunter dropped the bag and gave chase. The mouse darted in and chewed open the bag. The tortoise rolled into the bushes. The crow cawed loudly to warn them all when the hunter turned back.",
            "By the time the hunter returned, empty-handed and angry, the four friends were already laughing together by their pool.",
        ),
        "moral": "What no one can do alone, friends can do easily. Each gift is small until it is given together.",
        "sort_order": 14,
    },
    {
        "slug": "the-three-fish",
        "source": "Panchatantra",
        "title": "The Three Fish",
        "body": _p(
            "In a quiet lake lived three fish — one called Far-Sighted, one called Quick-Wit, and one called Whatever-Will-Be.",
            "One evening fishermen passed the lake and admired the fat fish leaping. ‘Tomorrow we bring our nets,’ they said.",
            "Far-Sighted heard them and at once swam down the stream that fed the lake, into a different river. ‘Better to leave before the trouble comes.’",
            "Quick-Wit stayed, but in the morning when the nets came he played dead, floated to the surface, was scooped up among other fish, and at the right moment slipped through a tear in the net into the river.",
            "Whatever-Will-Be did not move from his weed-bed. ‘Whatever fate decrees,’ he said, ‘will happen anyway.’ Fate decreed the fishermen’s frying-pan.",
        ),
        "moral": "Foresight escapes the net entirely; cleverness escapes from inside it; only laziness calls itself fate.",
        "sort_order": 15,
    },
    {
        "slug": "the-cat-and-the-sparrows",
        "source": "Hitopadesha",
        "title": "The Cat in the Tree",
        "body": _p(
            "On a great fig tree by a river lived a flock of sparrows. Below in a hollow at the foot of the tree lived a wicked cat who watched the chicks every day with hungry eyes.",
            "He thought: ‘If I steal one chick at night, the parents will move the whole flock. I must seem to be no danger at all.’ So he sat in the open, told a string of beads in his paws, and spoke gently and slowly to anyone who passed.",
            "Word spread that an ascetic had taken up residence under the tree. A blind hare came to live with him as a disciple. He even spared the hare for a long time, to keep up his disguise.",
            "Each night, while the parents slept, the cat slipped up the tree and ate one chick. The mothers wept and could not understand. The chicks vanished, one by one.",
            "At last a wise old crow noticed the bones in the cat’s hollow. He cawed the truth across the tree. The sparrows mobbed the cat all together, and the disguise was no protection at all.",
        ),
        "moral": "Beware the beggar with a sleek belly. A polite face on a hungry heart is the most dangerous mask.",
        "sort_order": 16,
    },
    {
        "slug": "the-heron-and-the-crab",
        "source": "Panchatantra",
        "title": "The Heron and the Crab",
        "body": _p(
            "An old heron, too tired to fish, sat by the pond and wept loudly. The fishes came up and asked what was wrong. ‘I have heard,’ said the heron, ‘that this pond is to be drained tomorrow. We shall all die.’",
            "The terrified fish begged him to save them. ‘Very well,’ said the heron. ‘I shall carry you, one at a time, to a deeper pond on the other side of the hill.’",
            "Each day the heron took one fish in his beak — and ate it on a flat rock just out of sight. He made many trips. Many fish.",
            "At last only an old crab remained. ‘Take me too,’ said the crab. The heron, full of fish for so many days, accepted gladly.",
            "As they flew, the crab looked down and saw the rock white with fish-bones. He clamped his great pincers around the heron’s long neck and held on with all his strength. The heron fell. The crab walked home, alone.",
        ),
        "moral": "A liar’s plan thrives only as long as no one looks back. The last in line is sometimes the cleverest.",
        "sort_order": 17,
    },
    {
        "slug": "the-lion-jackal-crow-camel",
        "source": "Panchatantra",
        "title": "The Lion, the Jackal, the Crow and the Camel",
        "body": _p(
            "A lion ruled a forest with three foul advisors — a jackal, a crow and a leopard. One day a stray camel, parted from his caravan, wandered in. The lion, gracious that morning, granted him refuge.",
            "But the lion fell ill. Game grew scarce. The three advisors, hungry, began to whisper: ‘The camel is a stranger. Why should we starve while he eats our king’s grass?’",
            "‘We cannot kill him outright,’ said the jackal, ‘the king has given his word. But what if he were to offer himself?’",
            "They went together before the lion. The jackal bowed: ‘Sire, take me, your servant, for your meal.’ The crow flapped: ‘No, take me!’ The leopard: ‘No, take me!’ Each was politely refused (by prior arrangement). The trusting camel, watching, thought: ‘I am a guest — I must do my part.’ He stepped forward. ‘Sire, take me.’",
            "The lion paused only a moment. The advisors did not.",
        ),
        "moral": "When the council whispers in unison, examine its motive. A trap is sometimes built by people taking turns to pretend they would walk into it.",
        "sort_order": 18,
    },
    {
        "slug": "tenali-and-the-three-dolls",
        "source": "Tenali Raman",
        "title": "Tenali and the Three Dolls",
        "body": _p(
            "A king from a far country sent King Krishnadevaraya three dolls. They looked exactly alike. ‘Tell me,’ wrote the foreign king, ‘which is the most valuable.’",
            "The court pundits examined them with magnifying glasses, weighed them, scratched them — and gave up. Tenali Raman picked up the dolls and looked at the small holes in each one’s ear.",
            "He took a fine wire. Into the first doll’s ear he pushed it; the wire came out of the other ear. Into the second doll’s ear; the wire came out of the mouth. Into the third doll’s ear; the wire stopped, and stayed inside.",
            "‘The first doll,’ said Tenali, ‘is the man who hears something and lets it out at once — useless. The second is the man who hears and tells it everywhere — dangerous. The third hears and keeps a secret. Of the three, only the third can be trusted.’",
            "The foreign king sent gold; the court pundits looked at the floor.",
        ),
        "moral": "A man worth keeping is one whose ears are doors that close. Knowing what to hold quiet is a skill of its own.",
        "sort_order": 19,
    },
    {
        "slug": "akbar-and-the-longest-line",
        "source": "Akbar-Birbal",
        "title": "The Longest Line",
        "body": _p(
            "Emperor Akbar drew a line on the floor of his court with a piece of chalk. ‘Make this line shorter,’ he said, ‘without rubbing out any part of it.’",
            "The pundits stared. Some said it was impossible. Some proposed clever tricks of optics. None pleased the emperor.",
            "Birbal walked up, took the chalk, and drew a longer line beside the first one. He bowed and stepped back.",
            "The original line had not been touched. But beside the new one, it was the shorter of the two.",
            "‘Make a thing small,’ said Birbal, ‘by raising up something next to it.’",
        ),
        "moral": "A problem you cannot attack head-on can sometimes be solved sideways. Greatness is comparison.",
        "sort_order": 20,
    },

    # ── Aesop & European fables (21-65) ──────────────
    {
        "slug": "the-tortoise-and-the-hare",
        "source": "Aesop",
        "title": "The Tortoise and the Hare",
        "body": _p(
            "The hare laughed at the tortoise for his small slow steps. ‘I could run twice round the meadow before you crossed it once.’ ‘Will you race me, then?’ said the tortoise quietly.",
            "All the animals came to watch. At the start the hare bounded ahead so fast he was out of sight in moments. The tortoise plodded on.",
            "Far ahead, the hare looked back and saw nothing. ‘He has not even reached the first turn. I have time for a long nap.’ He lay down under a tree and slept.",
            "The tortoise plodded on. The sun moved across the sky. The tortoise plodded on, past the sleeping hare, on toward the finishing post.",
            "The hare woke at the cheering and ran with all his might — but he reached the post just in time to see the tortoise cross it.",
        ),
        "moral": "Slow and steady, kept up faithfully, beats brilliance that stops to rest.",
        "sort_order": 21,
    },
    {
        "slug": "the-ant-and-the-grasshopper",
        "source": "Aesop",
        "title": "The Ant and the Grasshopper",
        "body": _p(
            "All summer long the grasshopper sang in the meadow while the ant marched grain after grain back to her nest. ‘Come and sing with me,’ called the grasshopper. ‘There is plenty of food everywhere.’ The ant did not look up.",
            "Then came the cold rain, and after that the snow. The fields lay bare. The grasshopper, thin and shivering, came to the ant’s door.",
            "‘Please — a little of your store. I am starving.’ ‘What did you do all summer?’ asked the ant. ‘I sang.’ ‘Then dance,’ said the ant, and shut the door.",
        ),
        "moral": "Do the work of the season while the season lasts; winter does not negotiate.",
        "sort_order": 22,
    },
    {
        "slug": "the-lion-and-the-mouse",
        "source": "Aesop",
        "title": "The Lion and the Mouse",
        "body": _p(
            "A lion was sleeping when a tiny mouse ran across his paw. The lion woke and pinned him with one claw. ‘Spare me, your majesty,’ squeaked the mouse. ‘One day I may save your life.’ The lion laughed and let him go.",
            "Some weeks later the lion was caught in a hunter’s rope net. He roared, but he could not break the cords. The mouse heard the roar and came running.",
            "Tiny tooth by tiny tooth, he chewed the ropes through. The lion stepped free.",
        ),
        "moral": "No friend is too small to be useful, and no kindness too small to be remembered.",
        "sort_order": 23,
    },
    {
        "slug": "the-fox-and-the-grapes",
        "source": "Aesop",
        "title": "The Fox and the Grapes",
        "body": _p(
            "A fox saw a fine bunch of grapes hanging high on a vine. They were ripe and dark and shining.",
            "He jumped, and missed. He jumped, and missed. He took a longer run, jumped, and missed. After many tries he sat down panting and looked up at the grapes.",
            "‘They are probably sour anyway,’ he said, and walked away.",
        ),
        "moral": "When we cannot have what we want, it comforts us to pretend we never wanted it.",
        "sort_order": 24,
    },
    {
        "slug": "the-wolf-and-the-lamb",
        "source": "Aesop",
        "title": "The Wolf and the Lamb",
        "body": _p(
            "A wolf met a lamb at a stream. ‘You are muddying my water!’ he growled. ‘How can I,’ said the lamb, ‘when I am downstream of you?’",
            "‘Then last year you insulted me,’ said the wolf. ‘I was not born last year.’ ‘Then it must have been your father.’ He sprang.",
        ),
        "moral": "A bad heart will find a reason. Argument with a tyrant only postpones the meal.",
        "sort_order": 25,
    },
    {
        "slug": "the-dog-and-his-reflection",
        "source": "Aesop",
        "title": "The Dog and His Reflection",
        "body": _p(
            "A dog crossed a footbridge with a piece of meat in his mouth. Looking down, he saw another dog in the water below, also holding meat — and the meat there looked larger than his own.",
            "He growled and snapped at the other dog to take its piece. His own meat fell into the water and was lost. The other dog vanished too.",
            "He went home with nothing.",
        ),
        "moral": "Grasp at more than you have, and you may end with less than you came with.",
        "sort_order": 26,
    },
    {
        "slug": "the-north-wind-and-the-sun",
        "source": "Aesop",
        "title": "The North Wind and the Sun",
        "body": _p(
            "The North Wind and the Sun argued about which of them was stronger. They saw a traveller walking down the road in a cloak. ‘Whichever of us makes him take off his cloak,’ they agreed, ‘is the stronger.’",
            "The North Wind blew a freezing gale. The traveller pulled his cloak around himself and held it tight. The Wind blew harder. The traveller wrapped himself tighter still.",
            "Then the Sun shone gently, and warmer, and warmer. The traveller loosened his cloak. He took it off and hung it over his arm.",
        ),
        "moral": "Warmth opens what force only closes more tightly.",
        "sort_order": 27,
    },
    {
        "slug": "town-mouse-country-mouse",
        "source": "Aesop",
        "title": "The Town Mouse and the Country Mouse",
        "body": _p(
            "A country mouse invited his cousin from town to dinner. He served beans, barley and a crust of cheese. The town mouse picked at the food. ‘Cousin, in town we eat far better. Come and see.’",
            "They went to town. In the great hall the table was spread with cakes and cheeses, fruits and meats. The country mouse marvelled — but just as he reached for the cheese, the door banged open and two huge dogs rushed in. The mice fled into the wall, hearts pounding.",
            "‘I am going home,’ said the country mouse. ‘Better beans in peace than cake in terror.’",
        ),
        "moral": "A simple meal eaten without fear is finer than a feast taken between alarms.",
        "sort_order": 28,
    },
    {
        "slug": "the-crow-and-the-pitcher",
        "source": "Aesop",
        "title": "The Crow and the Pitcher",
        "body": _p(
            "A thirsty crow found a pitcher with a little water at the bottom. His beak could not reach it. He pushed and pushed, but the pitcher would not tip.",
            "He thought. Then he picked up a pebble and dropped it into the pitcher. He picked up another, and another. The water rose. Stone by stone, the level climbed until it reached the rim.",
            "He drank, and flew on.",
        ),
        "moral": "What strength cannot win, patience and many small acts can. Slowly, slowly, the water rises.",
        "sort_order": 29,
    },
    {
        "slug": "the-goose-with-the-golden-eggs",
        "source": "Aesop",
        "title": "The Goose with the Golden Eggs",
        "body": _p(
            "A poor man had a goose that laid one golden egg every morning. Each day he sold the egg and grew a little richer.",
            "But he was impatient. ‘If she lays one a day, she must be full of gold inside. I shall have it all at once.’",
            "He killed the goose and cut her open. Inside was nothing but an ordinary goose. The eggs stopped, of course, that very day.",
        ),
        "moral": "The slow flow of a steady gift is more valuable than the lump that ends it.",
        "sort_order": 30,
    },
    {
        "slug": "the-milkmaid-and-her-pail",
        "source": "Aesop",
        "title": "The Milkmaid and Her Pail",
        "body": _p(
            "A milkmaid carried a pail of milk on her head, walking to market. As she walked she dreamed.",
            "‘With the milk-money I shall buy eggs. The eggs will hatch into chickens. The chickens will lay more eggs. I shall sell them and buy a fine dress and a ribbon. At the dance, the boys will all want me — but I shall toss my head at them like this —’",
            "She tossed her head. The pail fell. The milk ran across the road into the dust.",
        ),
        "moral": "Do not spend in dreams what you have not yet earned. Plans built on the next step skip the step underfoot.",
        "sort_order": 31,
    },
    {
        "slug": "the-fox-and-the-crow",
        "source": "Aesop",
        "title": "The Fox and the Crow",
        "body": _p(
            "A crow sat on a branch with a piece of cheese in her beak. A fox passed below and saw it.",
            "‘Beautiful crow,’ called the fox. ‘How glossy your wings! How proud your head! Surely a creature so handsome must have the finest voice of any bird.’",
            "The crow, delighted, opened her beak to sing. The cheese fell. The fox caught it.",
            "‘Lovely voice,’ said the fox over his shoulder, ‘but next time, lovely lady, beware of compliments.’",
        ),
        "moral": "Flattery is the song of someone who wants something. Listen carefully, and hold your cheese.",
        "sort_order": 32,
    },
    {
        "slug": "the-wolf-in-sheeps-clothing",
        "source": "Aesop",
        "title": "The Wolf in Sheep's Clothing",
        "body": _p(
            "A wolf, finding the flock too well-guarded for his usual tricks, came upon the skin of a sheep and pulled it on. He walked among the flock unnoticed and ate well for many nights.",
            "But one evening the shepherd, choosing a sheep for the next day’s meal, picked the fattest of all — which happened to be the wolf in his sheep’s clothing.",
            "He died as the disguise he had counted on.",
        ),
        "moral": "Disguise yourself well enough and you may pay the price of the costume.",
        "sort_order": 33,
    },
    {
        "slug": "the-bundle-of-sticks",
        "source": "Aesop",
        "title": "The Bundle of Sticks",
        "body": _p(
            "An old farmer had four sons who quarrelled all day. On his deathbed he called them and showed them a bundle of sticks tied together. ‘Break it.’",
            "Each son tried. The bundle did not bend. ‘Now untie it.’ They untied it. ‘Each take one, and break it.’ Each stick snapped easily.",
            "‘So it is with you,’ said the old man. ‘Together you cannot be broken. Apart, the smallest hand will snap you.’",
        ),
        "moral": "What hangs together stands; what falls apart breaks.",
        "sort_order": 34,
    },
    {
        "slug": "the-frog-and-the-ox",
        "source": "Aesop",
        "title": "The Frog and the Ox",
        "body": _p(
            "A small frog saw a great ox grazing in the meadow and was filled with envy. ‘I shall make myself as big as he is.’",
            "He took a deep breath and puffed out his sides. ‘Am I as big as he, children?’ ‘Not nearly,’ said his children. He puffed harder. ‘Now?’ ‘Not nearly.’ Once more, with all his strength —",
            "He burst.",
        ),
        "moral": "Stretching to be greater than your kind makes can crack the kind you are.",
        "sort_order": 35,
    },
    {
        "slug": "the-frogs-asking-for-a-king",
        "source": "Aesop",
        "title": "The Frogs Asking for a King",
        "body": _p(
            "The frogs of a quiet pond grew restless without a ruler. ‘Send us a king!’ they begged the gods. The gods dropped a great log into the pond. The frogs hid in the reeds and watched it.",
            "After a few days they saw it did not move. They climbed onto it, mocked it, danced on it. ‘This is a useless king. Send us a real one!’",
            "The gods sent a stork.",
            "She ate them, one after another.",
        ),
        "moral": "Be careful what you ask of the gods. A peaceful absence is sometimes better than a fierce presence.",
        "sort_order": 36,
    },
    {
        "slug": "the-bat-and-the-weasels",
        "source": "Aesop",
        "title": "The Bat and the Weasels",
        "body": _p(
            "A bat fell to the ground and was caught by a weasel. ‘I hate birds,’ said the weasel. ‘I am not a bird,’ said the bat. ‘See my fur? I am a mouse.’ The weasel let him go.",
            "Some days later the bat fell again, and was caught by another weasel. ‘I hate mice,’ said the weasel. ‘I am no mouse,’ said the bat. ‘See my wings? I am a bird.’ He was let go again.",
        ),
        "moral": "Be flexible enough to fit the moment, but stay one truthful self underneath.",
        "sort_order": 37,
    },
    {
        "slug": "the-eagle-and-the-arrow",
        "source": "Aesop",
        "title": "The Eagle and the Arrow",
        "body": _p(
            "An eagle was shot down out of a clear sky by an archer. As he lay dying he looked at the arrow in his side and saw that its shaft was fletched with an eagle’s own feathers.",
            "‘So,’ he said quietly, ‘we give the means of our own fall.’",
        ),
        "moral": "What we contribute carelessly to the world may one day be aimed back at us.",
        "sort_order": 38,
    },
    {
        "slug": "the-old-man-and-death",
        "source": "Aesop",
        "title": "The Old Man and Death",
        "body": _p(
            "An old man, weary from carrying a load of sticks home through the heat, dropped his bundle by the side of the road. ‘I wish Death would come and take me. Anything would be better than this.’",
            "Out of nowhere, Death appeared. ‘You called?’",
            "The old man swallowed. ‘Yes — if you would be so kind, please help me lift my bundle of sticks back onto my shoulder.’",
        ),
        "moral": "We long for an end mostly because the present is heavy. When the end actually arrives, the heaviness suddenly seems bearable.",
        "sort_order": 39,
    },
    {
        "slug": "the-cat-and-the-mice-bell",
        "source": "Aesop",
        "title": "Belling the Cat",
        "body": _p(
            "The mice held a council. ‘The cat is too quiet — she is upon us before we hear her. Who has a plan?’",
            "A young mouse stood up. ‘Tie a bell around her neck. Then we shall always hear her coming.’ The mice cheered.",
            "An old mouse cleared his throat. ‘An excellent plan. But which of us shall tie the bell on the cat?’",
            "Silence.",
        ),
        "moral": "It is easy to propose what is hard to do. The plan is not the plan until someone has agreed to carry it out.",
        "sort_order": 40,
    },
    {
        "slug": "the-donkey-in-the-lions-skin",
        "source": "Aesop",
        "title": "The Donkey in the Lion's Skin",
        "body": _p(
            "A donkey found a lion’s skin lying in the grass and pulled it on. He went around the forest, and all the animals fled before him. He felt very grand.",
            "He came to a herd of cattle and brayed loudly to scare them. The bray gave him away.",
            "The cattle laughed and chased him out.",
        ),
        "moral": "A borrowed skin lasts only until you open your mouth.",
        "sort_order": 41,
    },
    {
        "slug": "the-wolf-and-the-crane",
        "source": "Aesop",
        "title": "The Wolf and the Crane",
        "body": _p(
            "A wolf got a bone stuck in his throat. He promised a great reward to anyone who could remove it. A long-necked crane reached down into the wolf’s throat and pulled out the bone.",
            "‘Now my reward,’ said the crane.",
            "‘Reward?’ said the wolf. ‘You put your head into the mouth of a wolf, and you took it out again unbitten. Be glad of that.’",
        ),
        "moral": "When you do a favour for the wicked, the favour itself may be all you ever get back.",
        "sort_order": 42,
    },
    {
        "slug": "the-mountain-in-labour",
        "source": "Aesop",
        "title": "The Mountain in Labour",
        "body": _p(
            "A great mountain began to groan and shake. The earth trembled. Birds fled. People came from miles around to see what tremendous thing the mountain was about to bring forth.",
            "After hours of rumbling, the mountain split — and out came a small mouse.",
            "The mouse ran away into the grass.",
        ),
        "moral": "Great noise often gives birth to small things. Beware the trumpet that introduces nothing.",
        "sort_order": 43,
    },
    {
        "slug": "the-bear-and-two-travellers",
        "source": "Aesop",
        "title": "The Bear and the Two Travellers",
        "body": _p(
            "Two travellers were walking through the forest. They had sworn to stand by each other in any danger. A bear suddenly came out of the trees.",
            "The first man scrambled up a tree without a word. The second, alone, threw himself face down and held very still — for he had heard that bears do not touch the dead.",
            "The bear sniffed at his ear and went away. The first man climbed down. ‘What did the bear whisper to you?’",
            "‘She said: never trust a friend who deserts you in danger.’",
        ),
        "moral": "A friend you discover only in fair weather is no friend at all.",
        "sort_order": 44,
    },
    {
        "slug": "the-stag-at-the-pool",
        "source": "Aesop",
        "title": "The Stag at the Pool",
        "body": _p(
            "A stag came to a pool to drink and saw himself in the water. He admired his great antlers. ‘What a crown!’ Then he saw his thin legs and was ashamed. ‘How spindly. How ugly.’",
            "A pack of dogs broke from the trees. He bolted. His thin legs carried him faster than the dogs could run — until his great antlers caught in a low branch.",
            "He was held there until the dogs reached him.",
        ),
        "moral": "We sometimes despise what carries us and admire what hangs us.",
        "sort_order": 45,
    },
    {
        "slug": "the-two-pots",
        "source": "Aesop",
        "title": "The Two Pots",
        "body": _p(
            "A river in flood swept two pots from a kitchen — one of brass, one of clay. As they bobbed along together, the brass pot called: ‘Friend, stay close to me. I shall protect you.’",
            "‘Thank you,’ said the clay pot, ‘but please keep your distance. Whether the river throws you against me, or me against you, the breaking will be all on my side.’",
        ),
        "moral": "Be wary of friendships where the other can survive what would shatter you.",
        "sort_order": 46,
    },
    {
        "slug": "the-donkey-and-the-salt",
        "source": "Aesop",
        "title": "The Donkey and the Salt",
        "body": _p(
            "A trader’s donkey carried a heavy load of salt. Crossing a stream, he stumbled and fell in. When he stood up the salt had dissolved away. The load was light. He was very pleased.",
            "The next day the trader loaded him with cotton. At the same stream the donkey deliberately let himself fall — and the cotton drank up so much water that he could barely stand again.",
            "He limped the rest of the way under three times the weight.",
        ),
        "moral": "A trick that worked once may break you the second time. Conditions are part of the lesson.",
        "sort_order": 47,
    },
    {
        "slug": "the-fox-and-the-stork",
        "source": "Aesop",
        "title": "The Fox and the Stork",
        "body": _p(
            "A fox invited a stork to dinner and served soup in a flat dish. The fox lapped it up. The stork could not get her long beak into a single drop. She went home hungry.",
            "Some days later she invited the fox to dinner. She served the soup in a tall narrow jar. The stork dipped her beak in easily. The fox could not reach.",
            "‘I learned this,’ said the stork sweetly, ‘from a friend.’",
        ),
        "moral": "What you do to others is the menu they will set before you.",
        "sort_order": 48,
    },
    {
        "slug": "the-dog-in-the-manger",
        "source": "Aesop",
        "title": "The Dog in the Manger",
        "body": _p(
            "A dog lay down in a manger full of hay. He could not eat hay himself, but every time the cattle came near to feed he snarled at them and snapped.",
            "‘Selfish creature,’ said the ox at last. ‘You will not eat the hay yourself, and you will not let those who can.’",
        ),
        "moral": "It is meanness of the worst kind to deny others what does us no good.",
        "sort_order": 49,
    },
    {
        "slug": "the-hare-and-the-frogs",
        "source": "Aesop",
        "title": "The Hares and the Frogs",
        "body": _p(
            "The hares lived in such fear of dogs and eagles and men that one day they all decided to drown themselves and have done with it. They ran together to a great pond.",
            "As they reached the bank, all the frogs sitting there leapt in terror into the water and dived to the bottom.",
            "The hares paused. ‘Well,’ said one, ‘there are creatures more frightened than ourselves.’ They turned and went home.",
        ),
        "moral": "There is always someone whose fear makes ours look smaller. Misery, looked at fairly, is rarely the worst in the world.",
        "sort_order": 50,
    },
    {
        "slug": "the-old-lion-and-the-fox",
        "source": "Aesop",
        "title": "The Old Lion and the Fox",
        "body": _p(
            "An old lion, too weak to hunt, lay in his cave and pretended to be sick. The animals came one by one to pay their respects — and went into the cave, but never came out.",
            "A fox stopped at the entrance. ‘How are you, sire?’ ‘Come in, friend, come closer.’",
            "‘Forgive me, sire — I see many footprints going in, and not one coming out.’",
        ),
        "moral": "Watch the door before you walk through it. The wise notice not where everyone is, but where they have all gone.",
        "sort_order": 51,
    },
    {
        "slug": "the-eagle-and-the-fox",
        "source": "Aesop",
        "title": "The Eagle and the Fox",
        "body": _p(
            "An eagle and a fox were friends. The eagle nested in a high tree, the fox raised her cubs in the bushes below.",
            "One day food was scarce, and the eagle, knowing the fox was out, swept down and carried off her cubs. She could do nothing — she could not climb to the nest.",
            "Soon afterwards a piece of burning meat from a sacrifice on a nearby altar caught in the eagle’s twigs. The nest blazed. The young eagles, half-feathered, fell to the ground. The fox came out and ate them.",
        ),
        "moral": "Wronging a friend you think powerless invites a justice you did not see coming.",
        "sort_order": 52,
    },
    {
        "slug": "the-astronomer",
        "source": "Aesop",
        "title": "The Astronomer",
        "body": _p(
            "An astronomer used to walk every night with his eyes fixed on the stars, studying their motions. One evening he was crossing a field, lost in the heavens, when he stepped straight into a deep well.",
            "His cries brought a passer-by, who pulled him out. ‘Friend, you watch the stars so carefully — could you not have spared a glance for the ground at your feet?’",
        ),
        "moral": "There is nothing wrong with watching the stars, but the path beneath you also asks for attention.",
        "sort_order": 53,
    },
    {
        "slug": "the-fisherman-and-the-little-fish",
        "source": "Aesop",
        "title": "The Fisherman and the Little Fish",
        "body": _p(
            "A fisherman pulled a tiny fish out of the river. ‘Please throw me back,’ said the fish. ‘I am too small to be worth eating. Wait until I am grown, then catch me again — I shall make a fine meal.’",
            "‘Little fool,’ said the fisherman. ‘A small certain meal is better than a large one I shall probably never see again.’",
        ),
        "moral": "A bird in hand is worth two in the river. Trade certainty for hope only when the trade is fair.",
        "sort_order": 54,
    },
    {
        "slug": "the-lion-and-the-statue",
        "source": "Aesop",
        "title": "The Lion and the Statue",
        "body": _p(
            "A man and a lion were walking together and arguing about which was the stronger. They came to a public square where stood a statue of a hero killing a lion.",
            "‘Look,’ said the man triumphantly, ‘there is the proof.’",
            "‘That,’ said the lion, ‘was carved by a man. If lions had carved it, the statue would have looked very different.’",
        ),
        "moral": "Listen to the storytellers, but remember the storyteller is on one side. The lion has not been heard.",
        "sort_order": 55,
    },
    {
        "slug": "the-trumpeter-taken-prisoner",
        "source": "Aesop",
        "title": "The Trumpeter Taken Prisoner",
        "body": _p(
            "A trumpeter was captured in battle. ‘Spare me,’ he cried. ‘I am not a soldier — I have killed no one. I only blow my trumpet.’",
            "‘That is exactly why we must not spare you,’ said his captor. ‘You yourself have not lifted a sword. But your trumpet has set a thousand swords lifting in others. You stir the violence you do not commit.’",
        ),
        "moral": "Those who urge others on share in the deed. Words can be edges that cut without ever being held.",
        "sort_order": 56,
    },
    {
        "slug": "the-two-crabs",
        "source": "Aesop",
        "title": "The Two Crabs",
        "body": _p(
            "‘My child,’ said the mother crab, ‘why do you walk so awkwardly, sideways like that? You should walk straight ahead.’",
            "‘Show me how, mother,’ said the little crab, ‘and I shall do it.’",
            "She tried, but no crab can walk straight. She was as sideways as her child.",
        ),
        "moral": "Practise what you would teach. Lessons taught only with the tongue do not travel.",
        "sort_order": 57,
    },
    {
        "slug": "the-boy-bathing",
        "source": "Aesop",
        "title": "The Boy Bathing",
        "body": _p(
            "A boy in a river was sinking. He cried for help to a man on the bank. The man stopped and began to scold him. ‘Foolish child! Why did you go in where it was deep? You ought to have known better.’",
            "‘Sir,’ gasped the boy, ‘help me out first. Lecture me afterwards.’",
        ),
        "moral": "Save the drowning before you debate them. There is a time for sermons and a time for hands.",
        "sort_order": 58,
    },
    {
        "slug": "the-mice-in-the-cheese",
        "source": "Aesop",
        "title": "The Mice and the Cheese",
        "body": _p(
            "A great cheese was found by a band of mice. They argued about how to divide it. ‘Let us call upon the cat,’ said one foolish mouse. ‘She will be fair.’",
            "The cat was delighted to come. She measured the cheese very carefully into three equal heaps. ‘But this one,’ she said, ‘is a hair larger.’ She bit a piece. ‘Now this one is too large.’ She bit a piece. So she went, balancing and biting, until the cheese was gone.",
        ),
        "moral": "Do not appoint the wolf to settle quarrels among the lambs. The arbitrator’s motive is the first thing to weigh.",
        "sort_order": 59,
    },
    {
        "slug": "the-boasting-traveller",
        "source": "Aesop",
        "title": "The Boasting Traveller",
        "body": _p(
            "A man newly returned from his travels boasted in the market about his deeds. ‘In Rhodes,’ he said, ‘I leapt further than any man living. Anyone in Rhodes will tell you so.’",
            "A bystander pointed at the ground. ‘Friend, here is Rhodes. Leap here.’",
        ),
        "moral": "Show, do not tell. The proof of a leaper is a leap, here, today, in front of us.",
        "sort_order": 60,
    },
    {
        "slug": "the-wind-and-the-tree",
        "source": "Aesop",
        "title": "The Reed and the Oak",
        "body": _p(
            "An oak and a reed grew on a riverbank. ‘Look at you,’ said the oak. ‘Bending at every breath of wind. I stand straight no matter how it blows.’",
            "A great storm came that night. The reed bent flat to the ground; the wind passed over. The oak stood firm — until a single mighty gust tore him out by the roots.",
            "When the storm cleared, the reed lifted itself again, unhurt.",
        ),
        "moral": "Bending is not weakness. The straightest pride is sometimes uprooted while the soft head goes on living.",
        "sort_order": 61,
    },
    {
        "slug": "the-sick-lion",
        "source": "Aesop",
        "title": "The Sick Lion",
        "body": _p(
            "A lion grew old and sick and could not hunt. He lay in his cave and was visited by every animal — except the donkey, who came up boldly to mock him.",
            "‘See now,’ said the donkey to the others, ‘even the king of beasts is brought low. He cannot answer me back.’",
            "He kicked the lion as he left.",
            "It was not the donkey who suffered most that day; the lion bore the kick. But the donkey’s shame was larger and longer-lived than his pleasure.",
        ),
        "moral": "Mocking the fallen says more about the mocker than the fallen.",
        "sort_order": 62,
    },
    {
        "slug": "the-bear-and-the-bees",
        "source": "Aesop",
        "title": "The Bear and the Bees",
        "body": _p(
            "A bear was stung by a single bee. In a rage he tore at the hive with both paws.",
            "Out came the swarm. They covered him in a cloud and stung him from end to end. He fled, howling, into the river.",
        ),
        "moral": "A small wrong returned with anger pulls down a thousand wrongs in answer.",
        "sort_order": 63,
    },
    {
        "slug": "the-old-woman-and-the-doctor",
        "source": "Aesop",
        "title": "The Old Woman and the Doctor",
        "body": _p(
            "An old woman, nearly blind, called a doctor and promised to pay him a great sum if he restored her sight. He came each day. While he treated her eyes he also quietly carried away pieces of furniture from her room.",
            "When her sight was restored she looked around. ‘My house is empty!’ she cried. ‘I will not pay.’",
            "The doctor took her to court. The judge asked the woman why she refused. ‘Sir, the doctor said he would restore my sight. He has not. Before, I could see all my furniture in my house. Now, with these clear eyes, I see none of it.’",
        ),
        "moral": "Promised cures sometimes deliver more illness than they remove. Look at the price.",
        "sort_order": 64,
    },
    {
        "slug": "the-hen-and-the-golden-treasure",
        "source": "Aesop",
        "title": "The Widow and the Hen",
        "body": _p(
            "A widow had a hen that laid one egg every day. ‘If I gave her twice the grain,’ she thought, ‘she would lay twice the eggs.’",
            "She doubled the hen’s feed. The hen grew so fat she could not lay at all.",
        ),
        "moral": "More is not always better. The right amount of anything is rarer than too much.",
        "sort_order": 65,
    },

    # ── Jataka Tales (66-75) ──────────────
    {
        "slug": "the-banyan-deer",
        "source": "Jataka",
        "title": "The Banyan Deer",
        "body": _p(
            "Long ago, the Bodhisattva was born as a stately deer with a golden coat — the king of the Banyan Deer. In the same forest there was another deer-king, the Branch Deer. Both herds lived in a royal park where the king of the country hunted.",
            "Each day the king would shoot many deer, often wounding many to kill one. The two deer-kings made a pact: each day one deer from each herd would be chosen by lot and offered, so the rest could live in peace.",
            "One day the lot fell on a young hind in the Branch herd, who was great with fawn. ‘Spare me until my child is born,’ she begged. The Branch king refused. She went to the Banyan king. ‘Go in peace,’ he said. ‘I shall take your place.’",
            "He walked alone to the killing-block and lay down. The country’s king arrived and saw him. ‘You are the chief of the deer. I gave my word you would not be killed. Why are you here?’",
            "The Banyan king told him. The country’s king set down his bow. ‘Today,’ he said, ‘I grant the lives of all deer in the forest. Even your name, friend, I shall not kill again.’",
        ),
        "moral": "True kingship lays down its own life for the unprotected. Greatness is the willingness to take another’s place.",
        "sort_order": 66,
    },
    {
        "slug": "the-quarrel-of-the-quails",
        "source": "Jataka",
        "title": "The Quarrel of the Quails",
        "body": _p(
            "A flock of quails lived in a bamboo grove. A fowler often spread his net over them, then clapped his hands; the frightened quails would fly up together — but the net would catch them all.",
            "Their wise leader said: ‘When the net falls again, each of you put your head through one mesh. Then together, on my word, lift. The net will lift with you, and we shall fly to a thorn-bush and tip the net into it. The fowler will spend hours getting it back. We shall escape.’",
            "It worked. Day after day. The fowler was bewildered.",
            "But one day, while feeding, two quails quarrelled over a single seed. ‘I touched it first!’ ‘I saw it first!’ When the net fell that morning, instead of lifting together they argued: ‘You lift!’ ‘No, you lift!’",
            "The fowler caught them all.",
        ),
        "moral": "United, the smallest creatures lift the heaviest weight. Quarrel, and the lightest weight is enough.",
        "sort_order": 67,
    },
    {
        "slug": "the-monkey-king-and-the-bridge",
        "source": "Jataka",
        "title": "The Monkey King and the Bridge",
        "body": _p(
            "On the bank of the Ganga grew a great mango tree, and in it lived a king of monkeys with eighty thousand of his kind. He guarded one branch carefully — the branch that hung out over the river — for he knew if the king of men should ever taste those mangoes, he would come to take them all.",
            "One ripe fruit fell into the water and floated downstream. The king of men, bathing far below, found it. He ordered the tree found.",
            "Soldiers surrounded the tree by night, bows drawn for dawn. The monkey king saw them and his heart broke for his people. He climbed to the top, leapt across the river to a great bamboo on the other side, fastened the bamboo with a vine to his own foot, and stretched his body across as a bridge.",
            "‘Run over me,’ he called. The eighty thousand monkeys ran across his back to safety. The vine was a little short; the strain was terrible. By the time the last monkey was over, his spine was broken.",
            "The king of men, watching from below, lowered his bow. ‘There stretches across the river a king greater than I am.’",
        ),
        "moral": "A leader’s body is the bridge. The greatness of a king is measured in what crosses safely on his back.",
        "sort_order": 68,
    },
    {
        "slug": "the-merchant-of-seri",
        "source": "Jataka",
        "title": "The Merchant of Seri",
        "body": _p(
            "Two pedlars travelled a land selling pots and beads. One was honest; the other greedy. They agreed each would work alone, in different streets, then meet by night.",
            "In a poor old house lived a grandmother and her granddaughter. Hidden in a basket was a great gold bowl, blackened with soot — long forgotten. The little girl asked the greedy pedlar to trade beads for the ‘old metal pot.’ He scratched it; saw gold; saw a fortune. ‘Worthless,’ he said, planning to come back later for it cheap. He left.",
            "Soon the honest pedlar came by. The same trade was offered. He scratched it; saw gold. ‘Grandmother,’ he said, ‘this is gold worth a hundred thousand. I cannot buy it from you, but I shall give you what I have for it.’ He gave her every coin he carried, all his goods, kept only his scales, and walked away with the bowl.",
            "The greedy pedlar returned that evening. ‘I shall give you eight beads for that pot.’ ‘That pot,’ said the grandmother, ‘has gone with a kind man for a hundred thousand.’ The greedy man’s rage burst him.",
        ),
        "moral": "The honest merchant earns the treasure that the greedy merchant only intended to steal.",
        "sort_order": 69,
    },
    {
        "slug": "the-goat-that-laughed-and-wept",
        "source": "Jataka",
        "title": "The Goat That Laughed and Wept",
        "body": _p(
            "A wealthy brahmin bought a goat for a great sacrifice. As the servants washed the goat at the river, the goat suddenly laughed aloud — then burst into tears.",
            "The brahmin called him. ‘Why do you laugh and then weep?’ The goat (who was the Bodhisattva in that birth) answered: ‘I laughed because in five hundred lives I, too, was a sacrificing brahmin, and now this is my five-hundredth death by the knife — at last my cycle ends. I wept because I saw what awaits you next.’",
            "The brahmin set down the knife.",
            "‘Sir,’ he said, ‘I will not kill you, even if it costs me the merit of every sacrifice.’ But the goat had been promised in the rite. As the brahmin tried to free him, lightning struck a near tree and a falling branch killed the goat instantly.",
            "The brahmin, with the rest of his life, did no more sacrifices.",
        ),
        "moral": "Take care what cycle you set in motion. What you do to another is what you arrange to be done to yourself.",
        "sort_order": 70,
    },
    {
        "slug": "the-wise-old-bird",
        "source": "Jataka",
        "title": "The Wise Old Bird",
        "body": _p(
            "A flock of birds nested in the branches of a great tree. The oldest among them, watching one autumn, saw a small creeper sprouting at the foot of the trunk. ‘Pull it up,’ he told the young birds, ‘before it grows.’ ‘It is only a thread,’ they laughed. ‘What harm can a thread do?’",
            "Years later, hunters came along that road. The thread had grown into a stout liana. They cut it, twisted it into a strong rope, made nets, and that very year caught hundreds of birds in the great tree.",
        ),
        "moral": "The small thing today is the trap tomorrow. Listen to the old who saw the seedling.",
        "sort_order": 71,
    },
    {
        "slug": "the-sandy-road",
        "source": "Jataka",
        "title": "The Sandy Road",
        "body": _p(
            "A merchant led his caravan across a great desert. The route was so cruel they travelled only by night, by the stars; in daytime the sand was unbearable. The pilot of the caravan steered as a sailor steers, by the constellations.",
            "On the last night, exhausted, he fell asleep at his post. The bullocks turned. By morning the caravan was back at its previous evening’s camp. The water-jars were empty. There was no time for another night.",
            "The men despaired and lay down. The merchant did not. ‘There must be water somewhere here.’ He walked, looking. He found a single tuft of green grass on the sand. ‘Where there is grass, there is water below.’",
            "He told the men to dig. They dug a long time and struck rock. The men gave up. The merchant did not. He climbed into the pit, set the great rock against the side, and struck it with an iron crowbar. It split.",
            "Beneath was a cool spring. The caravan was saved.",
        ),
        "moral": "When others sit down in the desert, the leader keeps walking. The water is always one strike below the rock.",
        "sort_order": 72,
    },
    {
        "slug": "the-king-and-the-elephant",
        "source": "Jataka",
        "title": "The King and the Elephant",
        "body": _p(
            "A king once owned a great elephant who had served him for many years in battle. When the elephant grew old he was put to work hauling logs. One day he sat down in the road and would not move.",
            "The mahout came running. The king was sent for. The royal physician examined the elephant: there was nothing wrong with him.",
            "An old courtier walked round the elephant, looked at him sadly, and said: ‘Sire, this beast was once a hero of yours. He has heard the rope-master treat him today as if he were a common ox. He is not lazy, sire. His honour is wounded.’",
            "The king laid his hand on the elephant’s side. ‘Old friend, forgive us. From this day on, you shall be hauled, not haul.’",
            "The elephant rose and walked beside the king to the city.",
        ),
        "moral": "Honour, once given, cannot be taken back without breaking the one you gave it to. Old loyalty asks for old respect.",
        "sort_order": 73,
    },
    {
        "slug": "the-parrot-and-the-fig-tree",
        "source": "Jataka",
        "title": "The Parrot and the Fig Tree",
        "body": _p(
            "On a great fig tree by a river lived a flock of parrots. The fruit was endless, and they were content. Year after year they ate.",
            "One winter the tree grew old and stopped fruiting. Branch by branch it died. The flock left, one by one, for greener forests. Only one parrot stayed. He pecked at the rotting bark for what food was left, and slept under what dry leaves remained.",
            "The god Indra, watching from his sky, came down in the form of a goose. ‘Why do you stay? There is nothing left for you.’ ‘When the tree was full I ate of it,’ said the parrot. ‘When it has fallen on hard times, shall I be the first to leave it? It fed me for many years.’",
            "Indra was moved. He restored the tree to full fruit. The flock came back. The faithful parrot was given the highest branch.",
        ),
        "moral": "Those who fed you in good times deserve your loyalty in lean ones. A fair-weather friend has nothing of friendship in him.",
        "sort_order": 74,
    },
    {
        "slug": "the-three-fishes-jataka",
        "source": "Jataka",
        "title": "The Three Fishes",
        "body": _p(
            "In a river there once lived three fishes called Forethought, Presence-of-Mind, and Comes-What-May. The first heard fishermen scouting and quietly led his family upstream to a safer water. The second chose to stay, but kept his wits sharp.",
            "When the nets came down, Forethought was already far away. Presence-of-Mind, caught with the rest, hung very still and let himself be lifted out as if dead, then with one twist sprang free at the bank.",
            "Comes-What-May had said: ‘Whatever happens will happen.’ He had not moved when warned, and did not move when caught.",
            "He happened to be supper.",
        ),
        "moral": "Foresight saves you before the danger; presence of mind saves you inside the danger; doing nothing only makes the danger easier.",
        "sort_order": 75,
    },

    # ── Tenali Raman & Akbar-Birbal more (76-85) ──────────────
    {
        "slug": "tenali-and-the-cat",
        "source": "Tenali Raman",
        "title": "Tenali Raman and the Cat",
        "body": _p(
            "King Krishnadevaraya was vexed that mice were eating the palace grain. ‘Distribute a cat to every household in Vijayanagara,’ he ordered, ‘and a measure of milk a day to feed each cat. The mice will be ended.’",
            "Tenali Raman received his cat and his milk like everyone else. But on the very first day, he heated the milk to boiling and set it before the cat. The poor cat drank, burned its tongue badly, and from that day fled at the sight of milk.",
            "Some weeks later the king sent inspectors round to confirm the cats were well-fed. ‘Sire,’ said Raman’s inspector, returning, ‘Raman’s cat will not even look at milk.’",
            "Curious, the king came in person. He poured fresh milk before the cat. The cat ran. ‘Astonishing,’ said the king. ‘What does this mean?’",
            "‘It means, sire, that even cats remember a burn. And it means that royal orders, well-meant but not thought through, sometimes train cats not to drink milk and citizens to grumble. Perhaps the mice could be ended another way.’",
        ),
        "moral": "Sweeping orders meet small workarounds. Listen to those who do the work before drawing the policy.",
        "sort_order": 76,
    },
    {
        "slug": "tenali-and-the-pundit",
        "source": "Tenali Raman",
        "title": "Tenali and the Visiting Pundit",
        "body": _p(
            "A famous pundit came to Vijayanagara claiming to know all the scriptures by heart. He challenged the court. None could match him. The king grew uneasy: a defeated court was a humiliated kingdom.",
            "Tenali Raman bowed and stepped forward. He carried a great cloth-wrapped bundle, set it on the floor, and said: ‘Sir, this is a book my grandfather wrote. No one has been able to recite it. If you, who know all books, can recite even a verse, my king will reward you.’",
            "The pundit unwrapped the bundle. It was full of palm-leaves bound at one end — but every leaf was blank.",
            "‘There is nothing here.’ ‘Quite so,’ said Tenali. ‘But a man who knows all books should know even those that have not been written. Recite, if you please.’",
            "The pundit left the city by the next gate.",
        ),
        "moral": "A claim to know everything is undone by one polite request to recite the impossible.",
        "sort_order": 77,
    },
    {
        "slug": "akbar-and-the-crow-count",
        "source": "Akbar-Birbal",
        "title": "How Many Crows in Agra?",
        "body": _p(
            "Akbar one day, watching crows in the garden, asked the court: ‘How many crows are there in the city of Agra?’ The pundits coughed. ‘Birbal — how many?’",
            "Birbal answered without hesitation: ‘Eighty-three thousand four hundred and twenty-seven, your majesty.’",
            "‘And if I have my men go and count them, and find more or fewer?’",
            "‘If there are more, sire, it is because some have flown in from neighbouring kingdoms to visit. If there are fewer, some have flown out to visit relatives. The number I have given is the count at this exact moment.’",
            "Akbar laughed and gave him a purse.",
        ),
        "moral": "Confidence with a graceful bridge for being wrong is its own kind of wisdom.",
        "sort_order": 78,
    },
    {
        "slug": "birbal-the-honest-thief",
        "source": "Akbar-Birbal",
        "title": "Birbal Catches the Thief",
        "body": _p(
            "A jeweller had been robbed and suspected one of his six servants. Akbar asked Birbal to find the thief. Birbal called all six and gave each a stick of equal length.",
            "‘These are magic sticks,’ he said gravely. ‘Take them home tonight and sleep with them under your pillows. The stick of the thief will grow two finger-widths longer by morning.’",
            "In the morning the six servants returned. Five of the sticks were exactly as Birbal had given them. One was two finger-widths shorter.",
            "Birbal pointed at the man with the short stick. ‘Why is yours short?’ The man went pale. He had cut his stick in the night, terrified that the magic would lengthen it and reveal him.",
        ),
        "moral": "A guilty mind acts before it is asked. Honest hands leave the stick alone.",
        "sort_order": 79,
    },
    {
        "slug": "akbar-and-the-mango",
        "source": "Akbar-Birbal",
        "title": "Akbar and the Mango",
        "body": _p(
            "Akbar found a fine ripe mango in the palace garden. He set it carefully on his desk to enjoy after his meeting. While he was away, his nephew came in, ate the mango, and threw the stone in the wastebasket.",
            "Returning, the emperor was furious. He gathered the household and demanded to know who had eaten his mango. ‘Whoever did this,’ he stormed, ‘shall be flogged.’",
            "Birbal stepped in. ‘Sire, I have a way to find out without question.’ He brought a basin of water. ‘Each person will eat a piece of bread, then drink a sip of water. If they have eaten mango, the water will turn pink.’",
            "Down the line he went. Each ate, each sipped, each held up a clear cup. When he came to the nephew, the nephew refused. ‘I have not eaten — I refuse the test.’",
            "‘Why refuse,’ asked Birbal, ‘if you have nothing to hide?’",
        ),
        "moral": "Guilt avoids the test before the test is even given. Truth has nothing to fear from a clear glass.",
        "sort_order": 80,
    },
    {
        "slug": "tenali-and-the-fortune-teller",
        "source": "Tenali Raman",
        "title": "Tenali and the Fortune-Teller",
        "body": _p(
            "A fortune-teller arrived in Vijayanagara claiming he could foresee the day of any man’s death. People flocked to him in fear; the city was in a low mood.",
            "Tenali Raman went to the king. ‘Sire, allow me to speak to him in your court.’",
            "The fortune-teller arrived, confident. Tenali asked: ‘Tell me, sir — when will you die?’",
            "The man hesitated. ‘On a Tuesday, in my eighty-third year.’",
            "‘In that case,’ said Tenali, ‘sire, please order that he be hanged today, which is a Wednesday in his fortieth year. If he survives, he is a true prophet.’",
            "The fortune-teller turned and ran.",
        ),
        "moral": "A prediction that cannot be tested is not a prediction at all. The first question for a prophet is the prophet’s own date.",
        "sort_order": 81,
    },
    {
        "slug": "birbal-and-the-pot-of-wisdom",
        "source": "Akbar-Birbal",
        "title": "Birbal and the Pot of Wisdom",
        "body": _p(
            "A foreign ambassador set down a brass pot before Akbar. ‘Empty it,’ he said. The pot was sealed. There was no opening. The court was puzzled.",
            "Birbal took the pot and tilted it. He felt the weight of liquid moving inside. He turned the pot until he found a tiny pinhole near the base. He turned the hole upward, and saw the trick — there was a way to fill but no way to pour out.",
            "He took a sharp awl, made a second hole at the bottom, and the liquid ran out cleanly into a basin.",
            "‘In your country,’ said Birbal, ‘perhaps a man receives wisdom but does not give it. In ours, what flows in must also flow out.’",
        ),
        "moral": "Knowledge held without sharing is like water sealed in a pot — it spoils alone.",
        "sort_order": 82,
    },
    {
        "slug": "tenali-and-the-thieves-second",
        "source": "Tenali Raman",
        "title": "Tenali and the Mango Tree",
        "body": _p(
            "King Krishnadevaraya planted a precious mango sapling in his private garden. Each evening he visited it. The next morning the gardener reported: someone had been stealing the buds.",
            "The king stationed guards. The buds still vanished. He was furious.",
            "Tenali Raman walked through the garden. He noticed the marks on the soft earth around the tree — not footprints of men, but tiny scratches. He looked up. Among the leaves perched a sleek black koel, plucking the buds for nesting material.",
            "‘Sire, the thief is feathered, not human. Punish your guards if you wish, but the bird will continue. Plant a thorn-fence; the bird will find another tree.’",
            "The king did so. Birds and gardeners both kept their heads.",
        ),
        "moral": "Look at the evidence before you punish. Sometimes the suspect was never guilty at all.",
        "sort_order": 83,
    },
    {
        "slug": "akbar-and-the-three-questions",
        "source": "Akbar-Birbal",
        "title": "The Three Questions",
        "body": _p(
            "A scholar from a far land came to Akbar with three questions. ‘Where is the centre of the earth? How many stars are there in the sky? How many men and how many women are there in the world?’",
            "Birbal answered. ‘The centre of the earth is exactly where I am pointing — here.’ He set a stake in the ground. ‘If you doubt it, measure from the stake in any direction.’",
            "‘The number of stars,’ he went on, ‘is exactly the number of hairs on this goat I have brought in. If you doubt me, count the hairs and the stars and check the answer.’",
            "‘And the third? It is impossible to count, because in your country and ours there are men who behave like women and women who lead like men. The list will not stay still long enough to total.’",
            "The scholar laughed and bowed.",
        ),
        "moral": "The wise answer impossible questions by showing they are improperly framed.",
        "sort_order": 84,
    },
    {
        "slug": "birbal-the-well-wedding",
        "source": "Akbar-Birbal",
        "title": "Birbal and the Well's Wedding",
        "body": _p(
            "A village man’s well went dry. He went to his neighbour and bought a new one. He paid the price in full and the deed was signed. But the next day the neighbour refused to let him draw water. ‘I sold you the well, not the water inside it.’",
            "The man went to court. Akbar asked Birbal to judge.",
            "Birbal called the neighbour. ‘Is this your water?’ ‘It is.’ ‘Then it is staying inside another man’s well. He has graciously housed your water for many years and asks no rent. Tomorrow you owe him fifty gold pieces in rent — or remove your water from his well.’",
            "The neighbour paled. ‘But I cannot remove water!’ ‘Then it is the buyer’s. As the well is.’",
        ),
        "moral": "A clever cheat undoes itself when its logic is taken seriously.",
        "sort_order": 85,
    },

    # ── Mulla Nasruddin (86-90) ──────────────
    {
        "slug": "nasruddin-and-the-key",
        "source": "Mulla Nasruddin",
        "title": "Looking Under the Lamp",
        "body": _p(
            "Mulla Nasruddin was crawling around under a streetlamp on his hands and knees. A friend stopped to help. ‘What have you lost, Mulla?’ ‘My key.’",
            "They searched together for a long time. At last the friend asked: ‘Where exactly did you drop it?’ ‘Inside my house.’ ‘Then why on earth are we looking out here?’",
            "‘Because,’ said the Mulla, ‘the light is better here.’",
        ),
        "moral": "We often search for answers where it is comfortable to look, not where the answers actually are.",
        "sort_order": 86,
    },
    {
        "slug": "nasruddin-eat-coat",
        "source": "Mulla Nasruddin",
        "title": "Eat, Coat, Eat",
        "body": _p(
            "Nasruddin came home from working in the fields and went straight to a wedding feast in his work clothes. The host turned him away at the door: ‘This is not the place for a beggar.’",
            "He went home, washed, put on his finest robe, and returned. He was welcomed with bows and led to the seat of honour.",
            "When the food arrived, the Mulla took the sleeve of his robe and dipped it into the soup. ‘Eat, coat, eat,’ he said. ‘Eat the rice. Eat the meat. Clearly all this was meant for you.’",
        ),
        "moral": "Honour given to the costume, not the person inside it, deserves a costume’s share of the meal.",
        "sort_order": 87,
    },
    {
        "slug": "nasruddin-cooking-on-tail",
        "source": "Mulla Nasruddin",
        "title": "Cooking on the Distant Flame",
        "body": _p(
            "Nasruddin made a wager with a rich man: he could spend a winter night standing up to his neck in a freezing pond, with no fire, and survive.",
            "He stood there all night. He survived. The rich man came in the morning. ‘How did you keep warm?’ ‘There was a candle on a far hill. I kept my eyes on it.’ ‘Then you cheated. The candle warmed you. No prize.’",
            "The next day Nasruddin invited the rich man to dinner. He sat him down at a table and waited. And waited. After three hours the rich man asked where the food was.",
            "Nasruddin pointed out of the window. ‘See that pot over there on the hill? It is cooking nicely. By the same candle that kept me warm.’",
        ),
        "moral": "Argue dishonestly, and the answer will arrive on the same logic the next day.",
        "sort_order": 88,
    },
    {
        "slug": "nasruddin-rope",
        "source": "Mulla Nasruddin",
        "title": "Nasruddin's Rope",
        "body": _p(
            "A neighbour came to Nasruddin and asked to borrow a length of rope.",
            "‘Sorry,’ said the Mulla, ‘I am using it to dry flour.’ ‘To dry flour? You cannot dry flour on a rope!’",
            "‘When you do not wish to lend something,’ said Nasruddin, ‘one excuse is as good as another.’",
        ),
        "moral": "An unwilling lender finds his reasons later. The first reason is often only the loudest.",
        "sort_order": 89,
    },
    {
        "slug": "nasruddin-pot-baby",
        "source": "Mulla Nasruddin",
        "title": "The Pot That Had a Baby",
        "body": _p(
            "Nasruddin borrowed a great cooking pot from his neighbour. When he returned it the next day, there was a small pot inside. ‘Your pot gave birth in the night,’ said the Mulla solemnly. ‘Both are yours.’",
            "The neighbour, delighted, accepted both.",
            "Some weeks later the Mulla borrowed the pot again, and this time did not return it. After many days the neighbour came asking. ‘Alas,’ said Nasruddin, ‘your pot has died.’ ‘Pots cannot die!’ ‘But yours could give birth.’",
        ),
        "moral": "What you accept gladly when convenient, you must accept again when it is not.",
        "sort_order": 90,
    },

    # ── Tolstoy & moral classics (91-95) ──────────────
    {
        "slug": "the-three-questions-tolstoy",
        "source": "Tolstoy",
        "title": "The Three Questions",
        "body": _p(
            "A king once decided that he would never fail at anything if he knew three things: when was the most important time to act, who was the most important person to listen to, and what was the most important thing to do.",
            "He asked his wisest scholars. They argued and gave many answers. The king was unsatisfied. So he disguised himself as a peasant and went to a hermit who lived alone in the woods.",
            "He found the old man digging beds in his garden. ‘Hermit, answer me my questions.’ The hermit said nothing and kept digging. The king grew tired and took the spade himself, dug for hours, and just as the sun set a wounded man stumbled out of the trees, bleeding from a knife-wound. The king and the hermit washed and bound his wounds and laid him in the cottage to sleep.",
            "In the morning the wounded man told the king: ‘I am your enemy. I came to kill you in the woods because you killed my brother. I waited at the path. Your bodyguards found me first and wounded me. I crawled here. You bound me up. I owe you my life. Forgive me.’ The king forgave him.",
            "The king turned to the hermit. ‘Old man, you have not answered me.’ ‘I have already,’ said the hermit. ‘When you helped me dig, that was the most important time. I was the most important person — for then I was the only one with you. Helping me was the most important thing. If you had not stayed, you would not have been here when the wounded man came; he would have died, and so might you.’",
            "‘There is no other time but now. The most important person is whoever is with you. The most important thing to do is to do them good.’",
        ),
        "moral": "Now is the only time you have. The person before you is the most important person. To do them good is the work.",
        "sort_order": 91,
    },
    {
        "slug": "where-love-is",
        "source": "Tolstoy",
        "title": "Where Love Is, There God Is",
        "body": _p(
            "An old shoemaker named Martin lived in a basement, mending boots, since the death of his wife and son. He had stopped going to church. One night he dreamed Christ said to him: ‘I shall come to you tomorrow.’",
            "All the next day, as Martin worked at his window, he watched the street. The first person he saw was an old man shovelling snow, blue with cold. Martin called him in for tea. The old man warmed himself and went on.",
            "Then a poor mother passed with a thin baby and no warm clothes. Martin gave her bread and an old shawl. She thanked him and went on. Then a market-woman caught a boy stealing an apple and shouted to call the police. Martin paid for the apple and made peace between them.",
            "Evening came. Martin sat down disappointed. ‘He did not come.’",
            "But that night he dreamed again, and saw the old man, the mother, the boy and the market-woman, each smiling at him in turn. ‘I came to you many times today,’ said the voice. ‘Each time you opened the door.’",
        ),
        "moral": "Love that is shown to the next person to walk through the door is shown to everything that matters.",
        "sort_order": 92,
    },
    {
        "slug": "how-much-land",
        "source": "Tolstoy",
        "title": "How Much Land Does a Man Need?",
        "body": _p(
            "A peasant named Pahom believed that if he only had enough land, he would never need anything else. He worked hard, bought a farm, then a larger one. He was always restless.",
            "He heard of a far country where land was sold cheaply by an unusual rule: a man paid one fixed price, then was allowed to walk all day from sunrise to sunset. Whatever ground he encircled before the sun set was his — but he had to return to the starting point, or he forfeited everything.",
            "Pahom paid. At dawn he set off, walking fast, marking the corners with his spade. Each new field was so beautiful he widened the path further. By midday his loop was vast. He turned for home — but he had circled too far.",
            "He ran. The sun fell. He ran harder. As the last edge of the sun touched the horizon he reached the start, gasping — and fell dead at the marker.",
            "His servant dug a grave. From his head to his heels, six feet long.",
            "Six feet. That, in the end, was how much land Pahom needed.",
        ),
        "moral": "Wanting more for the sake of more is a road that ends in the only piece of land that finally fits us.",
        "sort_order": 93,
    },
    {
        "slug": "the-emperors-new-clothes",
        "source": "Andersen",
        "title": "The Emperor's New Clothes",
        "body": _p(
            "An emperor loved fine clothes more than anything. Two travelling weavers came to court and offered to make him a suit of cloth so wonderful that it would be invisible to anyone unfit for their post or hopelessly stupid.",
            "The emperor paid them in gold. They set up an empty loom and pretended to weave. Each minister he sent to inspect saw nothing — but afraid to seem unfit, each praised the cloth.",
            "On the day of the parade, the weavers ‘dressed’ the emperor in nothing at all. He paraded through the city. The crowd, terrified to seem stupid, cheered the imaginary suit.",
            "Then a small child pointed and said clearly: ‘But he has nothing on at all!’",
            "The whisper passed through the crowd. The emperor felt the truth of it. He kept walking — for he knew he must finish the parade — but he never trusted weavers again.",
        ),
        "moral": "A child’s plain word can break a spell that the whole crowd was holding up by silence.",
        "sort_order": 94,
    },
    {
        "slug": "the-fisherman-and-his-wife",
        "source": "Grimm",
        "title": "The Fisherman and His Wife",
        "body": _p(
            "A poor fisherman caught a great flounder. The flounder begged to be released and revealed himself as an enchanted prince. The fisherman let him go without asking for anything. He went home empty-handed.",
            "His wife was furious. ‘Go back and ask for a small cottage at least, instead of our hut.’ He went. The flounder granted it.",
            "‘Now ask for a stone house.’ Granted. ‘A castle.’ Granted. ‘To be queen.’ Granted. ‘To be empress.’ Granted. ‘To be Pope.’ Granted.",
            "‘Now,’ said the wife, ‘ask that I become like God, and command the sun and the moon to rise at my word.’ The fisherman, sick at heart, went to the sea, which had grown dark and stormy. He spoke the wish. The flounder rose only briefly. ‘Go home. She is in your old hut again.’",
        ),
        "moral": "Greed is a staircase that always has another step. The only way down is back to the bottom — sometimes the only way the world will allow.",
        "sort_order": 95,
    },

    # ── Final Indian folk + closing (96-105) ──────────────
    {
        "slug": "the-honest-woodcutter",
        "source": "Aesop",
        "title": "The Honest Woodcutter",
        "body": _p(
            "A woodcutter was felling a tree by a river when his axe slipped from his hand and fell into the deep water. He sat by the bank and wept — without his axe he could not feed his family.",
            "Mercury, the messenger god, took pity on him and rose from the water holding a golden axe. ‘Is this yours?’ ‘No, sir.’ He dived again and rose with a silver axe. ‘And this?’ ‘No, sir.’ He dived a third time and rose with a plain iron axe. ‘That is mine.’",
            "Mercury, pleased with his honesty, gave him all three.",
            "When his neighbour heard, he went to the river and threw his own axe in deliberately, then wept loudly. Mercury rose with a golden axe. ‘Yes, that one is mine!’ Mercury sank back into the water and the man never saw any of his axes again.",
        ),
        "moral": "Honesty is a poor fisherman with the best catch. Greed is a clever fisherman who comes home with nothing.",
        "sort_order": 96,
    },
    {
        "slug": "the-wise-old-mother",
        "source": "Indian folk",
        "title": "The Old Mother in the Sack",
        "body": _p(
            "A king once decreed that all old people in his kingdom must be put to death — for they were idle mouths. Every village obeyed. One young farmer, however, could not bear it; he hid his old mother in a closet under the floor and brought her food in secret.",
            "A great famine came. There was no rain; the seed-corn had been eaten last winter. The king sent word: any farmer who could plant a crop this year would be rewarded greatly.",
            "The young farmer was in despair. ‘We have no seed.’ His mother in the closet whispered: ‘Plough up the path between your house and the road. Old men used to spill grain along the way. The seed will be there.’",
            "He did. The path sprouted thickly. He had a fine harvest while others starved. The king summoned him. ‘How did you do this?’ ‘Your majesty, my old mother told me.’",
            "The king sat very still. The next day he revoked the law.",
        ),
        "moral": "The old know things the young have not yet had time to learn. A society that buries its memory plants only on poor soil.",
        "sort_order": 97,
    },
    {
        "slug": "the-greedy-priest",
        "source": "Indian folk",
        "title": "The Priest and the Pot of Curd",
        "body": _p(
            "A priest received a pot of curd from a generous patron. He climbed the steps to his rooms and set the pot beside his cot. As he lay down he began to dream.",
            "‘With the curd-money I shall buy goats. The goats will give milk. I shall sell the milk and buy a buffalo. With the buffalo I shall earn enough for a wife. We shall have a son. He shall play in the courtyard. If he is naughty, I shall lift my staff thus —’",
            "He swung his arm in the dream. The arm struck the curd-pot. The pot rolled off the steps and broke. The yard-dog ate the curd.",
        ),
        "moral": "Acting on the imagined future spills the actual present. Build slowly; do not strike with what is only in the head.",
        "sort_order": 98,
    },
    {
        "slug": "the-gold-and-the-snake",
        "source": "Hitopadesha",
        "title": "The Gold and the Snake",
        "body": _p(
            "A poor farmer one morning saw a great cobra coiled in a corner of his field. Frightened, but pious, he placed a bowl of milk on a stone for the snake. The next morning he found a single gold coin in the bowl.",
            "Each day he placed milk; each day there was a coin. He grew comfortable.",
            "One day he had to travel and asked his son to feed the snake. The son saw the coin and thought: ‘If a single coin comes daily, the snake’s body must hold a treasure. I shall kill it and take all at once.’ He waited with a stick. When the snake came he struck — and missed.",
            "The cobra hissed and bit him. The boy died. When the farmer returned, the snake said quietly: ‘Tell your kindness from your son’s greed. He is gone. So am I.’ It glided away into the long grass and was never seen again. The bowl lay empty.",
        ),
        "moral": "What gives you a coin a day will not give you a hundred at once. Greed kills the slow gift.",
        "sort_order": 99,
    },
    {
        "slug": "the-talking-tortoise",
        "source": "Panchatantra",
        "title": "The Talking Tortoise's Cousin",
        "body": _p(
            "(A second-cousin tale to The Tortoise and the Geese.)",
            "A young tortoise lived alone in a small pond. The pond began to dry. A pair of cranes nesting nearby offered to fly him to a deep lake.",
            "‘But I cannot fly,’ said the tortoise. ‘Bite this stick at the centre,’ said the cranes. ‘We shall hold the ends. Whatever you do, do not open your mouth.’",
            "He bit the stick. They flew. As they passed over a herd of cowherd boys, the boys hooted: ‘Look! A flying snack!’",
            "The tortoise wanted to ask whether they had ever seen anything as fine as himself, suspended between two cranes.",
            "He thought better of it. He kept his mouth shut. He arrived at the lake.",
            "(His older cousin, in another tale, did not.)",
        ),
        "moral": "Sometimes the moral of a story is enough to teach the next student. Knowing the cousin’s fall, the tortoise this time keeps still.",
        "sort_order": 100,
    },
    {
        "slug": "the-lazy-king",
        "source": "Indian folk",
        "title": "The Lazy King",
        "body": _p(
            "A king grew so lazy that he ordered his servants to feed him, dress him, even speak to his ministers for him. He grew fat in his bed. Years passed. He hardly knew his own kingdom.",
            "One day enemies invaded. ‘Sire, lead the army!’ ‘Pick me up,’ said the king. They lifted him onto a horse. The horse, used to his weight, plodded slowly. The enemy watched and laughed and rolled the city walls.",
            "When he had lost everything, he sat on the bare ground and tried to remember how to stand by himself.",
            "He could not.",
        ),
        "moral": "A muscle never used will not save you on the day you need it. Practise standing while it is easy.",
        "sort_order": 101,
    },
    {
        "slug": "the-loyal-servant",
        "source": "Indian folk",
        "title": "The Loyal Servant",
        "body": _p(
            "A merchant set off for a distant fair with two servants and a chest of gold. On the road, robbers attacked at dusk. The first servant fled. The second stood fast, fought, and was wounded; the chest was taken anyway.",
            "Years later the merchant prospered again. The first servant came asking for his old place. ‘Master, I am ready to serve.’ The merchant looked at him kindly and said: ‘When you ran, you were honest about who you were. I shall be honest too: I cannot give a man my chest who has already shown he will run from it.’",
            "He turned to the wounded one. ‘Take what is in this room.’ Inside were the merchant’s deeds, signets, and rings.",
        ),
        "moral": "Loyalty is the only credential the future cannot forge.",
        "sort_order": 102,
    },
    {
        "slug": "the-pearl-in-the-ash",
        "source": "Indian folk",
        "title": "The Pearl in the Ash",
        "body": _p(
            "A wise old woman in a village had only one possession of value — a single great pearl that her husband had given her on their wedding day, fifty years before. She kept it hidden in the ashes of her hearth.",
            "One day a wandering monk visited. He admired her clean cottage and humble manner. As he left she pressed the pearl into his hand. ‘Take it. You will use it better than I.’",
            "The monk walked away. That night he could not sleep. He turned in his blanket. At dawn he came back.",
            "‘Mother, take this back. I have wandered the world and have given up everything. But you, in your hut, have given up something I could not — the only thing of value you owned, with no second thought. Whatever it is you have, please teach me.’",
        ),
        "moral": "Generosity costs the generous nothing inside, and asks the receiver everything. To give freely is the harder peace.",
        "sort_order": 103,
    },
    {
        "slug": "the-stone-soup",
        "source": "European folk",
        "title": "Stone Soup",
        "body": _p(
            "Three travellers came to a village where every door was locked. People had hidden their food, sure that strangers would only ask and never give. The travellers shrugged, lit a fire in the square, and put a great pot of water over it. They dropped in three smooth stones.",
            "A child wandered up. ‘What are you cooking?’ ‘Stone soup. The finest soup in the world. Especially if we had a carrot or two — but no matter.’ The child ran home and brought two carrots.",
            "An old woman: ‘— and a handful of barley would lift it.’ She brought barley. ‘— and a small bone, oh, but no matter.’ A boy fetched a bone. Then onions, then turnips, then thyme.",
            "When the soup was ready, the whole village ate together for the first time in years. They lifted out the three stones, washed them, and gave them back. ‘Travel well, friends. Bring the stones again.’",
        ),
        "moral": "Trust starts with one bowl of water and one stone. Each small gift unlocks the next.",
        "sort_order": 104,
    },
    {
        "slug": "the-empty-pot",
        "source": "Chinese folk",
        "title": "The Empty Pot",
        "body": _p(
            "An old emperor had no heir. He gathered the children of his land and gave each one a single seed. ‘Whoever brings me back the most beautiful flower in a year shall be my successor.’",
            "A boy named Ling planted his seed in his finest pot. He watered it. Nothing grew. He moved it to better soil. Nothing grew. He prayed. Nothing grew. The year passed and his pot was empty.",
            "On the day of judgement the children came in a long procession with brilliant blooms in their pots. Ling, ashamed, walked at the back with his empty pot, and stood before the emperor red with embarrassment.",
            "The emperor walked the line and frowned. He came at last to Ling. ‘Where did you get your seed?’ ‘From you, sire. I planted it. I tended it. Nothing grew.’ The emperor smiled.",
            "‘Children,’ he announced, ‘the seeds I gave you all were boiled. None of them could grow. Every flower in this room was grown from a seed found elsewhere. Only one of you had the courage to come empty-handed and tell me the truth. Ling will be your next emperor.’",
        ),
        "moral": "Where there is honesty there is courage; where there is courage there is the throne.",
        "sort_order": 105,
    },
]


# ─────────────────────── upsert ────────────────────────
def main():
    if not CORPUS:
        print("Empty corpus.")
        return

    # Deduplicate by slug just in case the file is edited carelessly.
    seen = set()
    rows = []
    for row in CORPUS:
        slug = row.get("slug")
        if not slug:
            print("WARN: skipping row without slug:", row.get("title"))
            continue
        if slug in seen:
            print(f"WARN: duplicate slug '{slug}' — keeping first")
            continue
        seen.add(slug)
        rows.append({
            "slug": slug,
            "source": row["source"],
            "title": row["title"],
            "body": row["body"],
            "moral": row["moral"],
            "sort_order": int(row.get("sort_order", 0)),
            "is_active": True,
        })

    headers = {
        **HEADERS,
        "Prefer": "resolution=merge-duplicates,return=minimal",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/rest/v1/bedtime_stories?on_conflict=slug"

    BATCH = 25
    n = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        r = _session.post(url, json=chunk, headers=headers, timeout=30)
        if r.status_code >= 400:
            print(f"ERROR upserting chunk {i}-{i+len(chunk)}: {r.status_code} {r.text[:300]}")
            r.raise_for_status()
        n += len(chunk)
        print(f"  upserted {n}/{len(rows)}")

    print(f"Done. {n} stories upserted into bedtime_stories.")


if __name__ == "__main__":
    main()
